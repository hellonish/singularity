"use client";

import "@/styles/report-content.css";
import "katex/dist/katex.min.css";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { RawResearchActivity } from "@/lib/research_activity_presenter";
import { phaseStoryboardContext } from "@/lib/research_activity_presenter";
import {
  ResearchOperationsFeed,
  RESEARCH_ACTIVITY_CAP,
} from "@/components/report/ResearchOperationsFeed";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Download } from "lucide-react";
import { reportsApi, threadsApi, jobsApi, ApiError } from "@/lib/api";
import { consumeSSE } from "@/lib/sse";
import { researchIntensityLabel } from "@/lib/utils";
import { ReportViewer, type TOCEntry } from "@/components/report/ReportViewer";
import { ReportTOC } from "@/components/report/ReportTOC";
import { SelectionToolbar } from "@/components/report/SelectionToolbar";
import { PatchModal } from "@/components/report/PatchModal";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { AppLogoMark } from "@/components/app-logo";
import { UserMenu } from "@/components/user-menu";
import { AccountReconnectPrompt } from "@/components/account_reconnect_prompt";

export default function ReportViewPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const reportId = params.id as string;
  const threadParam = searchParams.get("thread");
  const { status: authStatus, data: session } = useSession();
  const apiReady =
    authStatus === "authenticated" && Boolean(session?.accessToken);

  const jobParam = searchParams.get("job");

  const [tocEntries, setTocEntries] = useState<TOCEntry[]>([]);
  const [selectedText, setSelectedText] = useState("");
  const [patchModalOpen, setPatchModalOpen] = useState(false);
  const [patchConflict, setPatchConflict] = useState(false);

  const [trackedJobStatus, setTrackedJobStatus] = useState<string | null>(null);
  const [trackedJobPhase, setTrackedJobPhase] = useState<string | null>(null);
  const [trackedJobDesc, setTrackedJobDesc] = useState<string | null>(null);
  const [trackedJobError, setTrackedJobError] = useState<string | null>(null);
  const [trackedJobStartedAt, setTrackedJobStartedAt] = useState<string | null>(null);
  const [activityLog, setActivityLog] = useState<RawResearchActivity[]>([]);

  const { data: reportMeta, isLoading: metaLoading, isFetching: metaFetching } = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => reportsApi.get(reportId),
    enabled: !!reportId && apiReady,
    refetchInterval: (query) => {
      const d = query.state.data;
      if (!d || d.latest_version != null) return false;
      return 4000;
    },
  });

  const { data: versionContent, isLoading: contentLoading } = useQuery({
    queryKey: ["report-content", reportId, reportMeta?.latest_version],
    queryFn: () => reportsApi.getVersionContent(reportId, reportMeta!.latest_version!),
    enabled: !!reportMeta?.latest_version && apiReady,
  });

  const { data: versionsData } = useQuery({
    queryKey: ["report-versions", reportId],
    queryFn: () => reportsApi.getVersions(reportId),
    enabled: !!reportId && apiReady,
  });

  const { data: defaultThread } = useQuery({
    queryKey: ["report-default-thread", reportId],
    queryFn: () => reportsApi.defaultThread(reportId),
    enabled: !!reportId && apiReady,
  });

  const {
    data: explicitThreadBundle,
    isError: explicitThreadError,
  } = useQuery({
    queryKey: ["thread-detail", threadParam],
    queryFn: () => threadsApi.get(threadParam!),
    enabled: !!reportId && !!threadParam && apiReady,
    retry: false,
  });

  const activeThreadId = useMemo(() => {
    if (
      threadParam &&
      explicitThreadBundle?.thread.report_id === reportId
    ) {
      return threadParam;
    }
    if (threadParam && explicitThreadError) {
      return defaultThread?.id ?? null;
    }
    if (defaultThread) return defaultThread.id;
    return null;
  }, [
    threadParam,
    explicitThreadBundle,
    explicitThreadError,
    reportId,
    defaultThread,
  ]);

  useEffect(() => {
    if (!jobParam || !apiReady) return;
    let cancelled = false;

    async function trackJob() {
      try {
        const initial = await jobsApi.get(jobParam!);
        if (cancelled) return;

        setTrackedJobStatus(initial.status);
        setTrackedJobPhase(initial.current_phase);
        setTrackedJobStartedAt(initial.started_at);

        if (initial.status === "done") {
          queryClient.invalidateQueries({ queryKey: ["report", reportId] });
          queryClient.invalidateQueries({ queryKey: ["report-content", reportId] });
          router.replace(`/reports/${reportId}`);
          return;
        }
        if (initial.status === "failed" || initial.status === "cancelled") {
          setTrackedJobError(initial.error_detail);
          return;
        }

        const session = await import("next-auth/react").then((m) => m.getSession());
        const token = session?.accessToken as string | undefined;
        const url = jobsApi.eventsUrl(jobParam!, token);

        try {
          for await (const evt of consumeSSE(url, token)) {
            if (cancelled) break;
            const data = JSON.parse(evt.data);
            if (evt.event === "job_activity") {
              const row = data as Record<string, unknown>;
              const id = evt.id ?? `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
              const kind = typeof row.kind === "string" ? row.kind : "unknown";
              const phase = typeof row.phase === "string" ? row.phase : "planning";
              const entry: RawResearchActivity = {
                id,
                kind,
                phase,
                meta:
                  row.meta && typeof row.meta === "object" && row.meta !== null
                    ? (row.meta as Record<string, unknown>)
                    : undefined,
                elapsed_ms: typeof row.elapsed_ms === "number" ? row.elapsed_ms : undefined,
              };
              setActivityLog((prev) => {
                const next = [...prev, entry];
                if (next.length > RESEARCH_ACTIVITY_CAP) {
                  return next.slice(-RESEARCH_ACTIVITY_CAP);
                }
                return next;
              });
              continue;
            }
            if (data.phase !== undefined) setTrackedJobPhase(data.phase);
            if (typeof data.description === "string") setTrackedJobDesc(data.description);
            if (data.status) setTrackedJobStatus(data.status);

            if (evt.event === "job_done") {
              setTrackedJobStatus("done");
              queryClient.invalidateQueries({ queryKey: ["report", reportId] });
              queryClient.invalidateQueries({ queryKey: ["report-content", reportId] });
              router.replace(`/reports/${reportId}`);
              break;
            }
            if (evt.event === "job_error") {
              setTrackedJobStatus("failed");
              if (data.error) setTrackedJobError(data.error);
              break;
            }
            if (evt.event === "job_cancelled") {
              setTrackedJobStatus("cancelled");
              break;
            }
          }
        } catch {
          // SSE dropped — fall back to polling below
        }

        if (cancelled) return;

        // Polling fallback: kick in if SSE closed without terminal event
        const intervalId = setInterval(async () => {
          if (cancelled) { clearInterval(intervalId); return; }
          try {
            const j = await jobsApi.get(jobParam!);
            if (cancelled) return;
            if (j.current_phase) setTrackedJobPhase(j.current_phase);
            if (j.error_detail) setTrackedJobError(j.error_detail);
            setTrackedJobStatus(j.status);
            if (j.status === "done") {
              clearInterval(intervalId);
              queryClient.invalidateQueries({ queryKey: ["report", reportId] });
              queryClient.invalidateQueries({ queryKey: ["report-content", reportId] });
              router.replace(`/reports/${reportId}`);
            } else if (j.status === "failed" || j.status === "cancelled") {
              clearInterval(intervalId);
            }
          } catch { /* ignore */ }
        }, 3000);
        return () => clearInterval(intervalId);
      } catch {
        // ignore initial fetch failure
      }
    }

    trackJob();
    return () => { cancelled = true; };
  }, [jobParam, apiReady, reportId, queryClient, router]);

  const isLoading = metaLoading || contentLoading;
  const isEditable = !!versionContent && !isLoading;

  const handleSelection = useCallback((text: string, _headingSlug: string | null) => {
    setSelectedText(text);
  }, []);

  const handlePatch = useCallback(async (instruction: string) => {
    if (!versionContent) throw new Error("No version loaded");
    try {
      await reportsApi.patch(reportId, versionContent.version_num, {
        selected_text: selectedText,
        instruction,
        if_match: versionContent.etag,
      });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setPatchConflict(true);
      }
      throw e;
    }
    queryClient.invalidateQueries({ queryKey: ["report", reportId] });
    queryClient.invalidateQueries({ queryKey: ["report-content", reportId] });
    queryClient.invalidateQueries({ queryKey: ["report-versions", reportId] });
    setSelectedText("");
    setPatchModalOpen(false);
  }, [versionContent, reportId, selectedText, queryClient]);

  const handleExport = useCallback(() => {
    if (!versionContent) return;
    const url = reportsApi.exportUrl(reportId, versionContent.version_num, "html");
    window.open(url, "_blank");
  }, [reportId, versionContent]);

  const handleBackDashboard = useCallback(() => {
    router.push("/dashboard");
  }, [router]);

  if (authStatus === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--rpt-bg)" }}>
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#6366f1] border-t-transparent" />
      </div>
    );
  }

  if (authStatus === "unauthenticated") {
    router.push("/");
    return null;
  }

  if (
    authStatus === "authenticated" &&
    (!session?.accessToken || session?.error)
  ) {
    return <AccountReconnectPrompt />;
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--rpt-bg)" }}>
      <header
        className="fixed left-0 right-0 top-0 z-40 grid h-14 w-full grid-cols-[1fr_auto_1fr] items-center gap-2 px-5"
        style={{
          background: "rgba(255,255,255,0.95)",
          borderBottom: "1px solid #e5e2db",
          backdropFilter: "blur(8px)",
        }}
      >
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={() => router.push("/dashboard")}
            className="flex shrink-0 items-center gap-1.5 transition-colors"
            style={{ color: "#6b7280", fontFamily: "var(--mono)", fontSize: 12 }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#1a1a1a")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#6b7280")}
          >
            <ArrowLeft size={14} />
            Dashboard
          </button>
          {reportMeta && (
            <p
              className="min-w-0 truncate"
              style={{
                color: "#1a1a1a",
                fontFamily: "var(--serif)",
                fontStyle: "italic",
                fontWeight: 300,
                fontSize: 14,
              }}
            >
              {reportMeta.title || reportMeta.query}
            </p>
          )}
        </div>

        <div
          className="flex items-center gap-2 py-1 pl-1 pr-2"
          style={{
            background:
              "radial-gradient(ellipse 140% 200% at 50% 28%, rgba(255,255,255,1) 0%, rgba(255,255,255,0.98) 35%, rgba(255,255,255,0.92) 52%, rgba(255,255,255,0.72) 70%, rgba(255,255,255,0.28) 88%, rgba(255,255,255,0.06) 96%, rgba(255,255,255,0) 100%)",
          }}
        >
          <AppLogoMark className="h-8 w-8 shrink-0 object-contain" />
          <span className="text-base font-semibold tracking-tight text-[#111827]">Singularity</span>
        </div>

        <div className="flex flex-shrink-0 items-center justify-end gap-2">
          {versionContent && (
            <span
              style={{
                fontFamily: "var(--mono)",
                fontSize: 11,
                color: "#6b7280",
                background: "#f3f4f6",
                border: "1px solid #e5e2db",
                borderRadius: 6,
                padding: "2px 8px",
              }}
            >
              v{versionContent.version_num}
              {versionsData && versionsData.versions.length > 1 && (
                <span style={{ color: "#6366f1" }}> /{versionsData.versions.length}</span>
              )}
            </span>
          )}

          <button
            onClick={handleExport}
            title="Export as HTML"
            disabled={!isEditable}
            className="p-2 rounded-lg transition-colors disabled:opacity-30"
            style={{ color: "#6b7280" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#1a1a1a")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#6b7280")}
          >
            <Download size={15} />
          </button>

          <UserMenu />
        </div>
      </header>

      <AnimatePresence>
        {patchConflict && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="fixed top-14 left-0 right-0 z-30 flex items-center justify-between px-6 py-2.5"
            style={{
              background: "#c45c00",
              fontFamily: "var(--mono)",
              fontSize: 12,
              color: "white",
            }}
          >
            <span>Document was updated — reload to see the latest version before editing.</span>
            <button
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ["report-content", reportId] });
                setPatchConflict(false);
              }}
              style={{ textDecoration: "underline", cursor: "pointer" }}
            >
              Reload
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex min-h-[100dvh] flex-col pt-14 lg:h-[100dvh] lg:flex-row lg:min-h-0">
        <div className="min-h-[42vh] flex-1 min-w-0 overflow-y-auto lg:min-h-0 lg:h-full">
          {jobParam && trackedJobStatus && trackedJobStatus !== "done" && !versionContent ? (
            <ReportJobProgress
              status={trackedJobStatus}
              phase={trackedJobPhase}
              description={trackedJobDesc}
              error={trackedJobError}
              query={reportMeta?.query ?? null}
              startedAt={trackedJobStartedAt}
              activityEntries={activityLog}
              onBack={() => router.push("/dashboard")}
            />
          ) : isLoading ? (
            <LoadingSkeleton />
          ) : versionContent ? (
            <div className="report-page-layout" style={{ position: "relative" }}>
              <ReportTOC entries={tocEntries} />

              <div>
                <div
                  style={{
                    borderBottom: "0.5px solid var(--rpt-border-hi)",
                    paddingBottom: 32,
                    marginBottom: 48,
                  }}
                >
                  <div className="report-eyebrow">Research Report</div>
                  <h1 className="report-title-display">
                    {reportMeta?.title || reportMeta?.query}
                  </h1>
                  <div className="report-meta-strip">
                    {reportMeta?.strength != null && (
                      <span>
                        Intensity: {researchIntensityLabel(reportMeta.strength)} (
                        {reportMeta.strength})
                      </span>
                    )}
                    <span>·</span>
                    <span>{versionContent.char_count.toLocaleString()} chars</span>
                    <span>·</span>
                    <span>
                      {new Date(reportMeta?.created_at || "").toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </span>
                  </div>
                </div>

                <div style={{ position: "relative" }}>
                  <ReportViewer
                    content={versionContent.content}
                    onTOCReady={setTocEntries}
                    onSelection={handleSelection}
                  />
                  <SelectionToolbar
                    selectedText={selectedText}
                    onEdit={() => setPatchModalOpen(true)}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-4 px-6 py-16 text-center">
              <p
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 12,
                  color: "var(--rpt-text-dim)",
                  maxWidth: 420,
                  lineHeight: 1.5,
                }}
              >
                {reportMeta?.latest_version == null
                  ? "No report version yet. If generation is still running, this page will update automatically. If it failed (e.g. Qdrant unreachable), fix your worker env or start Qdrant, then try a new research job."
                  : "No content available"}
              </p>
              {reportMeta?.latest_version == null && metaFetching ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#6366f1] border-t-transparent" />
              ) : null}
              <button
                type="button"
                onClick={() => queryClient.invalidateQueries({ queryKey: ["report", reportId] })}
                className="rounded-lg border border-[#e5e2db] bg-white px-4 py-2 text-xs transition-colors hover:bg-[#f9fafb]"
                style={{ fontFamily: "var(--mono)", color: "#374151" }}
              >
                Refresh metadata
              </button>
            </div>
          )}
        </div>

        <div className="flex min-h-[48vh] w-full flex-col border-t border-neutral-200 bg-white lg:h-full lg:min-h-0 lg:w-[min(100%,440px)] lg:shrink-0 lg:border-l lg:border-t-0">
          {activeThreadId ? (
            <ChatPanel
              key={activeThreadId}
              threadId={activeThreadId}
              reportContent={versionContent?.content}
              reportScope
              reportHeading={
                reportMeta?.title?.trim() ||
                reportMeta?.query?.trim() ||
                null
              }
              placement="split"
              onClose={handleBackDashboard}
            />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-sm text-neutral-500">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-600" />
              <p>Loading chat…</p>
            </div>
          )}
        </div>
      </div>

      <PatchModal
        open={patchModalOpen}
        selectedText={selectedText}
        onClose={() => setPatchModalOpen(false)}
        onSubmit={handlePatch}
      />
    </div>
  );
}

const PHASE_LABELS: Record<string, string> = {
  planning: "Structuring report",
  retrieval: "Gathering sources",
  writing: "Drafting content",
  polish: "Polishing markdown",
};

const PHASE_ORDER = ["planning", "retrieval", "writing", "polish"];

function formatRunningFor(iso: string | null): string | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  const ms = Date.now() - t;
  if (ms < 0) return "0s";
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const rs = s % 60;
  if (m < 1) return `${rs}s`;
  if (m < 60) return `${m}m ${rs.toString().padStart(2, "0")}s`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return `${h}h ${rm}m`;
}

function ReportJobProgress({
  status,
  phase,
  description,
  error,
  query,
  startedAt,
  activityEntries,
  onBack,
}: {
  status: string;
  phase: string | null;
  description: string | null;
  error: string | null;
  query: string | null;
  startedAt: string | null;
  activityEntries: RawResearchActivity[];
  onBack: () => void;
}) {
  const isFailed = status === "failed" || status === "cancelled";
  const activeIdx = phase ? PHASE_ORDER.indexOf(phase) : -1;
  const isRunning = !isFailed && (status === "pending" || status === "running");
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!isRunning || !startedAt) return;
    const id = window.setInterval(() => setTick((x) => x + 1), 1000);
    return () => window.clearInterval(id);
  }, [isRunning, startedAt]);

  const runningFor = isRunning ? formatRunningFor(startedAt) : null;
  const elapsedMs = startedAt ? Date.now() - new Date(startedAt).getTime() : 0;
  const isStuck = isRunning && elapsedMs > 10 * 60 * 1000;
  const liveLine = phaseStoryboardContext(phase);

  return (
    <div className="flex h-full min-h-[60vh] w-full flex-col justify-center px-4 py-10 lg:px-10">
      <div
        className="mx-auto flex w-full max-w-6xl flex-col gap-10 lg:flex-row lg:items-start lg:gap-12"
      >
        <div className="w-full shrink-0 lg:max-w-[280px]">
          {query && (
            <div style={{ marginBottom: 28 }}>
              <div
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 10,
                  color: "var(--rpt-text-dim)",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  marginBottom: 6,
                }}
              >
                Research query
              </div>
              <p
                style={{
                  fontFamily: "'Newsreader', Georgia, serif",
                  fontStyle: "italic",
                  fontWeight: 300,
                  fontSize: 16,
                  lineHeight: 1.5,
                  color: "var(--rpt-text)",
                }}
              >
                {query}
              </p>
            </div>
          )}

          {isRunning && runningFor && (
            <div
              style={{
                fontFamily: "var(--mono)",
                fontSize: 11,
                color: "#374151",
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  background: "#6366f1",
                  animation: "pulse 1.2s ease-in-out infinite",
                }}
              />
              Running for {runningFor}
            </div>
          )}

          <p
            style={{
              fontFamily: "'Newsreader', Georgia, serif",
              fontSize: 14,
              fontStyle: "italic",
              color: "var(--rpt-text-dim)",
              lineHeight: 1.45,
              marginBottom: 20,
            }}
          >
            {liveLine}
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {PHASE_ORDER.map((p, i) => {
              const isDone = activeIdx > i || (isFailed && activeIdx >= i);
              const isActive = i === activeIdx && !isFailed;
              const isPending = i > activeIdx;

              return (
                <div
                  key={p}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    opacity: isPending ? 0.35 : 1,
                    transition: "opacity 0.3s",
                  }}
                >
                  <div
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: "50%",
                      flexShrink: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      background: isDone
                        ? "rgba(13,138,91,0.12)"
                        : isActive
                          ? "rgba(99,102,241,0.1)"
                          : "var(--rpt-bg3)",
                      border: isActive ? "1.5px solid rgba(99,102,241,0.4)" : "none",
                    }}
                  >
                    {isDone ? (
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path d="M2 5l2.5 2.5L8 3" stroke="#0d8a5b" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : isActive ? (
                      <div
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: "50%",
                          background: "#6366f1",
                          animation: "pulse 1.2s ease-in-out infinite",
                        }}
                      />
                    ) : null}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 12,
                        color: isActive ? "#1a1a1a" : isDone ? "#374151" : "var(--rpt-text-dim)",
                        fontWeight: isActive ? 500 : 400,
                      }}
                    >
                      {PHASE_LABELS[p]}
                    </div>
                    {isActive && description && (
                      <div
                        style={{
                          fontFamily: "var(--mono)",
                          fontSize: 11,
                          color: "var(--rpt-text-dim)",
                          marginTop: 2,
                        }}
                      >
                        {description}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {isFailed && (
            <div
              style={{
                marginTop: 24,
                borderRadius: 8,
                background: "rgba(220,38,38,0.06)",
                border: "1px solid rgba(220,38,38,0.15)",
                padding: "12px 14px",
              }}
            >
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "#b91c1c", marginBottom: 4, fontWeight: 500 }}>
                {status === "cancelled" ? "Job cancelled" : "Generation failed"}
              </div>
              {error && (
                <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "#dc2626", lineHeight: 1.5, wordBreak: "break-word" }}>
                  {error.length > 400 ? `${error.slice(0, 400)}…` : error}
                </div>
              )}
              <button
                type="button"
                onClick={onBack}
                style={{
                  marginTop: 10,
                  fontFamily: "var(--mono)",
                  fontSize: 11,
                  color: "#374151",
                  background: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: 6,
                  padding: "5px 12px",
                  cursor: "pointer",
                }}
              >
                ← Back to Dashboard
              </button>
            </div>
          )}

          {isStuck && (
            <div
              style={{
                marginTop: 24,
                borderRadius: 8,
                background: "rgba(234,179,8,0.06)",
                border: "1px solid rgba(234,179,8,0.25)",
                padding: "12px 14px",
              }}
            >
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "#92400e", marginBottom: 4, fontWeight: 500 }}>
                Taking longer than expected
              </div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "#b45309", lineHeight: 1.5 }}>
                The job has been running for {runningFor} with no completion. It may be stuck. You can wait or go back and retry.
              </div>
              <button
                type="button"
                onClick={onBack}
                style={{
                  marginTop: 10,
                  fontFamily: "var(--mono)",
                  fontSize: 11,
                  color: "#374151",
                  background: "white",
                  border: "1px solid #e5e7eb",
                  borderRadius: 6,
                  padding: "5px 12px",
                  cursor: "pointer",
                }}
              >
                ← Back to Dashboard
              </button>
            </div>
          )}

          {!isFailed && (status === "pending" || status === "running") && activeIdx === -1 && (
            <div
              style={{
                marginTop: 20,
                fontFamily: "var(--mono)",
                fontSize: 11,
                color: "var(--rpt-text-dim)",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <div className="h-3.5 w-3.5 animate-spin rounded-full border border-[#6366f1] border-t-transparent" />
              Queued — waiting for worker…
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <ResearchOperationsFeed rawEntries={activityEntries} isRunning={isRunning} />
        </div>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="report-page-layout">
      <div />
      <div style={{ paddingTop: 48 }}>
        <div
          style={{
            height: 12,
            width: 120,
            background: "var(--rpt-bg3)",
            borderRadius: 4,
            marginBottom: 24,
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
        <div
          style={{
            height: 32,
            width: "70%",
            background: "var(--rpt-bg3)",
            borderRadius: 4,
            marginBottom: 16,
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
        <div
          style={{
            height: 12,
            width: "40%",
            background: "var(--rpt-bg3)",
            borderRadius: 4,
            marginBottom: 48,
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
        {[100, 85, 95, 75, 90, 80, 92, 70, 88].map((w, i) => (
          <div
            key={i}
            style={{
              height: 14,
              width: `${w}%`,
              background: "var(--rpt-bg3)",
              borderRadius: 3,
              marginBottom: 12,
              animation: "pulse 1.5s ease-in-out infinite",
              animationDelay: `${i * 0.1}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
