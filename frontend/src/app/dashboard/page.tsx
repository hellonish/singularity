"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import {
  reportsApi,
  jobsApi,
  threadsApi,
  type ReportMeta,
  type JobResponse,
  type ThreadResponse,
} from "@/lib/api";
import { consumeSSE } from "@/lib/sse";
import { cn } from "@/lib/cn";
import { UserMenu } from "@/components/user-menu";
import { DeleteReportDialog } from "@/components/delete-report-dialog";
import { DeleteThreadDialog } from "@/components/delete_thread_dialog";
import {
  ChatPanel,
  type ChatPanelLaunchPayload,
} from "@/components/chat/ChatPanel";
import { ChatHistorySidebar } from "@/components/chat/chat_history_sidebar";

function ReportCard({
  report,
  onRequestDelete,
}: {
  report: ReportMeta;
  onRequestDelete: (r: ReportMeta) => void;
}) {
  const router = useRouter();
  const timeAgo = getTimeAgo(report.created_at);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.015, y: -2 }}
      transition={{ duration: 0.15 }}
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/reports/${report.id}`)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          router.push(`/reports/${report.id}`);
        }
      }}
      className="group relative w-full cursor-pointer text-left hover:shadow-[0_6px_20px_rgba(0,0,0,0.08)]"
      style={{
        background: "#ffffff",
        border: "0.5px solid rgba(0,0,0,0.08)",
        borderRadius: 12,
        padding: "16px 18px",
        paddingRight: 44,
        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
        transition: "box-shadow 0.15s",
      }}
    >
      <button
        type="button"
        aria-label={`Delete report: ${report.title || report.query}`}
        className="absolute right-2 top-2 z-10 rounded-lg p-2 text-[#9ca3af] opacity-80 transition-opacity hover:bg-red-50 hover:text-red-600 hover:opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:hover:opacity-100 focus:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onRequestDelete(report);
        }}
      >
        <Trash2 className="h-4 w-4" strokeWidth={1.75} />
      </button>
      <h3
        className="line-clamp-2 mb-2"
        style={{
          fontFamily: "'Newsreader', Georgia, serif",
          fontStyle: "italic",
          fontWeight: 300,
          fontSize: 15,
          lineHeight: 1.4,
          color: "#141210",
        }}
      >
        {report.title || report.query}
      </h3>

      {report.title && (
        <p
          className="line-clamp-1 mb-3"
          style={{ fontFamily: "var(--mono, 'JetBrains Mono', monospace)", fontSize: 11, color: "#6b7280" }}
        >
          {report.query}
        </p>
      )}

      <div
        className="flex items-center gap-3 flex-wrap"
        style={{ fontFamily: "var(--mono, 'JetBrains Mono', monospace)", fontSize: 11, color: "#6b7280" }}
      >
        <span>{timeAgo}</span>
        {report.latest_char_count && (
          <span>{Math.round(report.latest_char_count / 1000)}k chars</span>
        )}
        {report.latest_version && (
          <span
            style={{
              background: "rgba(26,111,212,0.08)",
              color: "#1a6fd4",
              borderRadius: 4,
              padding: "1px 6px",
              fontSize: 10,
            }}
          >
            v{report.latest_version}
          </span>
        )}
        <span
          style={{
            marginLeft: "auto",
            background: report.strength >= 7 ? "rgba(13,138,91,0.1)" : "rgba(196,92,0,0.1)",
            color: report.strength >= 7 ? "#0d8a5b" : "#c45c00",
            borderRadius: 4,
            padding: "1px 6px",
            fontSize: 10,
          }}
        >
          s{report.strength}
        </span>
      </div>
    </motion.div>
  );
}

function JobProgressOverlay({
  job,
  onClose,
}: {
  job: JobResponse;
  onClose: () => void;
}) {
  const [phase, setPhase] = useState(job.current_phase);
  const [status, setStatus] = useState(job.status);
  const [errorDetail, setErrorDetail] = useState<string | null>(job.error_detail);
  const router = useRouter();

  useEffect(() => {
    if (status === "done") {
      const timer = setTimeout(() => {
        router.push(`/reports/${job.report_id}`);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [status, job.report_id, router]);

  useEffect(() => {
    let cancelled = false;
    async function listen() {
      const session = await import("next-auth/react").then((m) => m.getSession());
      const token = session?.accessToken;
      const url = jobsApi.eventsUrl(job.job_id, token);
      try {
        for await (const event of consumeSSE(url, token as string | undefined)) {
          if (cancelled) break;
          const data = JSON.parse(event.data);
          if (data.phase) setPhase(data.phase);
          if (data.status) setStatus(data.status);
          if (data.error_detail) setErrorDetail(data.error_detail);
          if (event.event === "job_done") {
            setStatus("done");
            break;
          }
          if (event.event === "job_error") {
            setStatus("failed");
            if (data.error) setErrorDetail(data.error);
            break;
          }
          if (event.event === "job_cancelled") {
            setStatus("cancelled");
            break;
          }
        }
      } catch {
        // SSE failed; polling effect below still updates UI
      }
    }
    listen();
    return () => { cancelled = true; };
  }, [job.job_id]);

  useEffect(() => {
    let stop = false;
    let intervalId: ReturnType<typeof setInterval> | undefined;
    async function pollOnce() {
      if (stop) return;
      try {
        const j = await jobsApi.get(job.job_id);
        if (stop) return;
        if (j.current_phase) setPhase(j.current_phase);
        if (j.error_detail) setErrorDetail(j.error_detail);
        if (j.status === "done" || j.status === "failed" || j.status === "cancelled") {
          setStatus(j.status);
          if (intervalId != null) clearInterval(intervalId);
          return;
        }
        if (j.status === "running" || j.status === "pending") {
          setStatus(j.status);
        }
      } catch {
        // ignore transient errors
      }
    }
    void pollOnce();
    intervalId = setInterval(() => {
      void pollOnce();
    }, 3000);
    return () => {
      stop = true;
      if (intervalId != null) clearInterval(intervalId);
    };
  }, [job.job_id]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
    >
      <motion.div
        initial={{ scale: 0.95 }}
        animate={{ scale: 1 }}
        className="flex w-full max-w-md flex-col items-center gap-6 rounded-2xl border border-[#e5e2db] bg-white p-8"
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-indigo-50">
          {status === "done" ? (
            <svg className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : status === "failed" || status === "cancelled" ? (
            <svg className="h-8 w-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
          )}
        </div>

        <div className="text-center">
          <h3 className="text-lg font-medium text-[#1a1a1a]">
            {status === "done"
              ? "Report Complete"
              : status === "failed"
                ? "Report Failed"
                : status === "cancelled"
                  ? "Report Cancelled"
                  : "Generating Report..."}
          </h3>
          {phase && (status === "running" || status === "pending") && (
            <p className="mt-1 text-sm text-[#6b7280]">Phase: {phase}</p>
          )}
          {status === "failed" && errorDetail ? (
            <p className="mt-3 max-h-24 overflow-y-auto text-left text-xs leading-relaxed text-red-700" style={{ fontFamily: "var(--mono, monospace)" }}>
              {errorDetail.length > 400 ? `${errorDetail.slice(0, 400)}…` : errorDetail}
            </p>
          ) : null}
        </div>

        {(status === "failed" || status === "cancelled") && (
          <button
            onClick={onClose}
            className="rounded-full bg-[#f3f4f6] px-6 py-2 text-sm text-[#1a1a1a] hover:bg-[#e5e7eb]"
          >
            Dismiss
          </button>
        )}
      </motion.div>
    </motion.div>
  );
}

export default function DashboardPage() {
  const { status: authStatus } = useSession();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [barMode, setBarMode] = useState<"chat" | "research">("research");
  const [barExtended, setBarExtended] = useState(false);
  const [barJobStrength, setBarJobStrength] = useState(5);
  const [activeJob, setActiveJob] = useState<JobResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ReportMeta | null>(null);
  const [dashThreadId, setDashThreadId] = useState<string | null>(null);
  const [dashLaunch, setDashLaunch] = useState<ChatPanelLaunchPayload | null>(null);
  const [dashChatBusy, setDashChatBusy] = useState(false);
  const [chatSidebarCollapsed, setChatSidebarCollapsed] = useState(false);
  const [researchDockThreadId, setResearchDockThreadId] = useState<string | null>(null);
  const [deleteThreadTarget, setDeleteThreadTarget] = useState<ThreadResponse | null>(null);

  const { data: reportsData, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: () => reportsApi.list(),
    enabled: authStatus === "authenticated",
  });

  const { data: threadsRaw, isLoading: threadsLoading } = useQuery({
    queryKey: ["dashboard-threads"],
    queryFn: () => threadsApi.list(50),
    enabled: authStatus === "authenticated",
  });

  const standaloneThreads = (threadsRaw ?? []).filter((t) => t.report_id == null);

  const createJobMutation = useMutation({
    mutationFn: () => jobsApi.create(query, barJobStrength),
    onSuccess: async (job) => {
      setDashThreadId(null);
      setDashLaunch(null);
      setActiveJob(job);
      setQuery("");
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      try {
        const thread = await threadsApi.create(job.report_id);
        setResearchDockThreadId(thread.id);
      } catch (e) {
        console.error("Could not open follow-up chat for this report", e);
        setResearchDockThreadId(null);
      }
    },
  });

  const deleteReportMutation = useMutation({
    mutationFn: (id: string) => reportsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      setDeleteTarget(null);
    },
  });

  const deleteThreadMutation = useMutation({
    mutationFn: (id: string) => threadsApi.delete(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-threads"] });
      setDeleteThreadTarget(null);
      if (dashThreadId === deletedId) {
        setDashThreadId(null);
        setDashLaunch(null);
      }
    },
  });

  const handleBarSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const text = query.trim();
      if (!text) return;
      if (barMode === "research") {
        if (text.length < 10) return;
        createJobMutation.mutate();
        return;
      }
      setDashChatBusy(true);
      try {
        const thread = await threadsApi.create();
        setDashThreadId(thread.id);
        setDashLaunch({
          nonce: Date.now(),
          message: text,
          execution_mode: "chat",
          chat_variant: barExtended ? "extended" : "standard",
          research_strength: 5,
        });
        setQuery("");
        queryClient.invalidateQueries({ queryKey: ["dashboard-threads"] });
      } catch (err) {
        console.error("Failed to start chat thread", err);
      } finally {
        setDashChatBusy(false);
      }
    },
    [query, barMode, barExtended, createJobMutation, queryClient],
  );

  const handleDismissJobOverlay = useCallback(() => {
    setActiveJob(null);
    setResearchDockThreadId(null);
  }, []);

  const onLaunchConsumed = useCallback(() => {
    setDashLaunch(null);
  }, []);

  const handleCloseDashChat = useCallback(() => {
    setDashThreadId(null);
    setDashLaunch(null);
    queryClient.invalidateQueries({ queryKey: ["dashboard-threads"] });
  }, [queryClient]);

  const handleSelectSidebarThread = useCallback((id: string) => {
    setDashThreadId(id);
    setDashLaunch(null);
  }, []);

  const handleSidebarNewChat = useCallback(() => {
    setDashThreadId(null);
    setDashLaunch(null);
  }, []);

  if (authStatus === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  if (authStatus === "unauthenticated") {
    router.push("/");
    return null;
  }

  const reports = reportsData?.items || [];

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden">
      {/* Header */}
      <header className="shrink-0 border-b border-[#e5e2db] bg-white">
        <div className="flex w-full items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-sm font-semibold text-white">
            S
          </div>
          <span className="text-lg font-semibold text-[#111827]">Singularity</span>
        </div>
        <div className="flex items-center gap-3">
          <UserMenu />
        </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-row overflow-hidden">
        <ChatHistorySidebar
          collapsed={chatSidebarCollapsed}
          onToggleCollapsed={() => setChatSidebarCollapsed((c) => !c)}
          threads={standaloneThreads}
          selectedThreadId={dashThreadId}
          onSelectThread={handleSelectSidebarThread}
          onNewChat={handleSidebarNewChat}
          onRequestDelete={setDeleteThreadTarget}
          isLoading={threadsLoading}
        />

        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-[#f8fafc]">
          {dashThreadId ? (
            <ChatPanel
              key={dashThreadId}
              threadId={dashThreadId}
              placement="main"
              launchWith={dashLaunch}
              onLaunchConsumed={onLaunchConsumed}
              onClose={handleCloseDashChat}
            />
          ) : (
            <div className="flex min-h-0 w-full flex-1 flex-col overflow-y-auto overscroll-contain px-6 py-8">
              <div className="mb-6 flex items-center justify-between">
                <h2
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    color: "#6b7280",
                  }}
                >
                  Recent Projects
                </h2>
                <span className="text-sm text-[#6b7280]">{reports.length} reports</span>
              </div>

              {isLoading ? (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-36 animate-pulse rounded-2xl border border-[#e5e2db] bg-white"
                    />
                  ))}
                </div>
              ) : reports.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-1 flex-col items-center justify-center gap-5 py-20"
                >
                  <div
                    className="flex flex-col items-center gap-3 rounded-2xl px-8 py-10"
                    style={{
                      background: "#ffffff",
                      border: "0.5px solid rgba(0,0,0,0.08)",
                      maxWidth: 420,
                    }}
                  >
                    <p
                      style={{
                        fontFamily: "'Newsreader', Georgia, serif",
                        fontStyle: "italic",
                        fontWeight: 400,
                        fontSize: 28,
                        color: "#141210",
                        textAlign: "center",
                        lineHeight: 1.2,
                      }}
                    >
                      Start your first research project
                    </p>
                    <p
                      style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 12,
                        color: "#4b5563",
                        textAlign: "center",
                      }}
                    >
                      Type a topic below and press enter
                    </p>
                  </div>
                </motion.div>
              ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
                  {reports.map((report) => (
                    <ReportCard
                      key={report.id}
                      report={report}
                      onRequestDelete={setDeleteTarget}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </main>

        <AnimatePresence>
          {researchDockThreadId ? (
            <ChatPanel
              key={researchDockThreadId}
              threadId={researchDockThreadId}
              placement="dock"
              reportScope
              onClose={() => setResearchDockThreadId(null)}
            />
          ) : null}
        </AnimatePresence>
      </div>

      {!dashThreadId ? (
      <div className="sticky bottom-0 z-20 border-t border-neutral-200/80 bg-white/90 px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-sm sm:px-6">
        <form
          onSubmit={handleBarSubmit}
          className="w-full rounded-2xl border border-neutral-200/90 bg-neutral-50/50 p-2.5"
        >
          <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-2">
            <div className="inline-flex shrink-0 gap-0.5 rounded-lg bg-neutral-100/80 p-0.5">
              <button
                type="button"
                onClick={() => setBarMode("chat")}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium text-neutral-600 transition-colors",
                  barMode === "chat" && "bg-white text-neutral-900 shadow-sm",
                )}
              >
                Chat
              </button>
              <button
                type="button"
                onClick={() => setBarMode("research")}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium text-neutral-600 transition-colors",
                  barMode === "research" && "bg-white text-neutral-900 shadow-sm",
                )}
              >
                Research
              </button>
            </div>

            {barMode === "chat" ? (
              <div className="flex shrink-0 items-center gap-2">
                <span className="text-xs text-neutral-500">Extended</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={barExtended}
                  onClick={() => setBarExtended((v) => !v)}
                  className={cn(
                    "relative h-6 w-10 shrink-0 rounded-full p-px transition-colors",
                    barExtended ? "bg-neutral-800" : "bg-neutral-300",
                  )}
                >
                  <span
                  className={cn(
                    "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-[left,right] duration-200 ease-out",
                    barExtended
                        ? "left-auto right-px"
                        : "left-px right-auto",
                    )}
                  />
                </button>
              </div>
            ) : (
              <div className="flex min-w-0 flex-1 basis-[min(100%,14rem)] items-center gap-2 sm:basis-auto sm:max-w-md">
                <span className="shrink-0 text-xs text-neutral-500">Intensity</span>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={barJobStrength}
                  onChange={(e) => setBarJobStrength(Number(e.target.value))}
                  className="min-w-0 flex-1 accent-neutral-700"
                />
                <span className="w-4 shrink-0 text-right text-xs tabular-nums text-neutral-600">
                  {barJobStrength}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 rounded-xl border border-neutral-200 bg-white px-2 py-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                barMode === "research"
                  ? "New report topic (min. 10 characters)…"
                  : "Message…"
              }
              className="min-w-0 flex-1 bg-transparent py-2 pl-2 text-base text-neutral-900 outline-none placeholder:text-neutral-400"
              style={{ fontFamily: "var(--serif, 'Newsreader', Georgia, serif)" }}
            />
            <button
              type="submit"
              disabled={
                !query.trim() ||
                createJobMutation.isPending ||
                dashChatBusy ||
                (barMode === "research" && query.trim().length < 10)
              }
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white transition-opacity",
                query.trim() &&
                  !createJobMutation.isPending &&
                  !dashChatBusy &&
                  !(barMode === "research" && query.trim().length < 10)
                  ? "bg-neutral-900 hover:bg-neutral-800"
                  : "bg-neutral-200 text-neutral-400",
              )}
              aria-label={barMode === "research" ? "Start report" : "Send"}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </form>
      </div>
      ) : null}

      {/* Job progress overlay */}
      <AnimatePresence>
        {activeJob && (
          <JobProgressOverlay
            job={activeJob}
            onClose={handleDismissJobOverlay}
          />
        )}
      </AnimatePresence>

      <DeleteReportDialog
        report={deleteTarget}
        open={deleteTarget !== null}
        loading={deleteReportMutation.isPending}
        errorMessage={
          deleteReportMutation.isError && deleteReportMutation.error
            ? deleteReportMutation.error.message
            : null
        }
        onCancel={() => {
          if (!deleteReportMutation.isPending) {
            deleteReportMutation.reset();
            setDeleteTarget(null);
          }
        }}
        onConfirm={() => {
          if (deleteTarget) deleteReportMutation.mutate(deleteTarget.id);
        }}
      />

      <DeleteThreadDialog
        thread={deleteThreadTarget}
        open={deleteThreadTarget !== null}
        loading={deleteThreadMutation.isPending}
        errorMessage={
          deleteThreadMutation.isError && deleteThreadMutation.error
            ? deleteThreadMutation.error.message
            : null
        }
        onCancel={() => {
          if (!deleteThreadMutation.isPending) {
            deleteThreadMutation.reset();
            setDeleteThreadTarget(null);
          }
        }}
        onConfirm={() => {
          if (deleteThreadTarget) deleteThreadMutation.mutate(deleteThreadTarget.id);
        }}
      />
    </div>
  );
}

function getTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  const diffWeeks = Math.floor(diffDays / 7);
  if (diffWeeks < 4) return `${diffWeeks}w ago`;
  return date.toLocaleDateString();
}
