"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { LayoutGrid, Trash2 } from "lucide-react";
import {
  reportsApi,
  jobsApi,
  threadsApi,
  llmApi,
  DEFAULT_CHAT_MODEL_ID,
  type ReportMeta,
  type ThreadSummaryResponse,
} from "@/lib/api";
import { llmModelGroupsFromCatalog } from "@/lib/llm_model_groups";
import { ChatModelPicker } from "@/components/chat/ChatModelPicker";
import { showDebugMockResearchControls } from "@/lib/debug_research_mock";
import { cn } from "@/lib/cn";
import {
  formatRelative,
  truncateDisplayLabel,
  researchIntensityLabel,
  RESEARCH_INTENSITY_OPTIONS,
} from "@/lib/utils";
import { UserMenu } from "@/components/user-menu";
import { DeleteReportDialog } from "@/components/delete-report-dialog";
import { DeleteThreadDialog } from "@/components/delete_thread_dialog";
import {
  ChatPanel,
  type ChatPanelLaunchPayload,
} from "@/components/chat/ChatPanel";
import { ChatHistorySidebar } from "@/components/chat/chat_history_sidebar";
import { AppLogoMark } from "@/components/app-logo";
import { AccountReconnectPrompt } from "@/components/account_reconnect_prompt";

/** Matches `var(--rpt-bg)` — editorial paper, same family as the research report page */
const DASH_MAIN_BG_RGB = "247,245,240";

const chromePillStyle = {
  background: `radial-gradient(ellipse 145% 195% at 50% 22%, rgba(${DASH_MAIN_BG_RGB},0.99) 0%, rgba(${DASH_MAIN_BG_RGB},0.95) 38%, rgba(${DASH_MAIN_BG_RGB},0.82) 58%, rgba(${DASH_MAIN_BG_RGB},0.42) 80%, rgba(${DASH_MAIN_BG_RGB},0.08) 94%, rgba(${DASH_MAIN_BG_RGB},0) 100%)`,
} as const;

/**
 * Purpose: Replace the full-width header with centered brand + top-right controls.
 * Inputs: `onBackToProjects` when a thread is open (returns to the projects grid).
 * Outputs: Absolutely positioned layers; pointer-events pass through except interactive chips.
 * ConciseExplanation: Full-width short linear scrim matches main paper background with a dense opaque
 * top band; Projects sits beside the account menu as a matching minimal icon button.
 */
function DashboardMainFloatingChrome({
  onBackToProjects,
}: {
  onBackToProjects?: () => void;
}) {
  return (
    <>
      <div className="pointer-events-none absolute left-0 right-0 top-0 z-20 flex h-[5.5rem] justify-center pt-1.5">
        <div
          className="absolute left-0 right-0 top-0 h-full w-full"
          aria-hidden
          style={{
            background: `linear-gradient(180deg, rgb(${DASH_MAIN_BG_RGB}) 0%, rgb(${DASH_MAIN_BG_RGB}) 32%, rgba(${DASH_MAIN_BG_RGB},0.99) 48%, rgba(${DASH_MAIN_BG_RGB},0.94) 62%, rgba(${DASH_MAIN_BG_RGB},0.72) 76%, rgba(${DASH_MAIN_BG_RGB},0.32) 88%, rgba(${DASH_MAIN_BG_RGB},0.06) 96%, rgba(${DASH_MAIN_BG_RGB},0) 100%)`,
          }}
        />
        <div className="pointer-events-auto relative z-10 px-3">
          <div className="flex items-center gap-2.5 py-2 pl-1 pr-2">
            <AppLogoMark className="h-10 w-10 shrink-0 object-contain" priority />
            <span className="text-lg font-semibold tracking-tight text-[#111827]">
              Singularity
            </span>
          </div>
        </div>
      </div>
      <div className="pointer-events-none absolute right-3 top-2 z-30 flex items-center gap-1.5 sm:right-5 sm:top-3">
        {onBackToProjects ? (
          <div className="pointer-events-auto rounded-full p-1" style={chromePillStyle}>
            <button
              type="button"
              onClick={onBackToProjects}
              className="flex h-8 w-8 items-center justify-center rounded-full text-neutral-600 transition-colors hover:bg-black/5"
              title="Projects"
              aria-label="Back to projects"
            >
              <LayoutGrid className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </div>
        ) : null}
        <div className="pointer-events-auto rounded-full p-1" style={chromePillStyle}>
          <UserMenu />
        </div>
      </div>
    </>
  );
}

function ReportCard({
  report,
  onRequestDelete,
}: {
  report: ReportMeta;
  onRequestDelete: (r: ReportMeta) => void;
}) {
  const router = useRouter();
  const timeAgo = formatRelative(report.created_at);

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
            background:
              report.strength === 3
                ? "rgba(13,138,91,0.1)"
                : report.strength === 1
                  ? "rgba(196,92,0,0.1)"
                  : "rgba(180,130,0,0.12)",
            color:
              report.strength === 3
                ? "#0d8a5b"
                : report.strength === 1
                  ? "#c45c00"
                  : "#92400e",
            borderRadius: 4,
            padding: "1px 6px",
            fontSize: 10,
          }}
        >
          {researchIntensityLabel(report.strength)}
        </span>
      </div>
    </motion.div>
  );
}


export default function DashboardPage() {
  const { status: authStatus, data: session } = useSession();
  const apiReady =
    authStatus === "authenticated" && Boolean(session?.accessToken);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [barMode, setBarMode] = useState<"chat" | "research">("research");
  const [barExtended, setBarExtended] = useState(false);
  const [barJobStrength, setBarJobStrength] = useState<1 | 2 | 3>(2);
  const [barDebugMockResearch, setBarDebugMockResearch] = useState(false);
  const [barModelId, setBarModelId] = useState(DEFAULT_CHAT_MODEL_ID);
  const [deleteTarget, setDeleteTarget] = useState<ReportMeta | null>(null);
  const [dashThreadId, setDashThreadId] = useState<string | null>(null);
  const [dashLaunch, setDashLaunch] = useState<ChatPanelLaunchPayload | null>(null);
  const [dashChatBusy, setDashChatBusy] = useState(false);
  const [chatSidebarCollapsed, setChatSidebarCollapsed] = useState(false);
  const [researchDockThreadId, setResearchDockThreadId] = useState<string | null>(null);
  const [researchDockReportId, setResearchDockReportId] = useState<string | null>(null);
  const [deleteThreadTarget, setDeleteThreadTarget] = useState<ThreadSummaryResponse | null>(null);

  const { data: reportsData, isLoading: reportsQueryLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: () => reportsApi.list(),
    enabled: apiReady,
  });

  const { data: threadsRaw, isLoading: threadsQueryLoading } = useQuery({
    queryKey: ["dashboard-threads"],
    queryFn: () => threadsApi.list(50),
    enabled: apiReady,
  });

  const { data: llmCatalog, isLoading: llmCatalogLoading } = useQuery({
    queryKey: ["llm-catalog"],
    queryFn: () => llmApi.models(),
    enabled: apiReady,
    staleTime: 120_000,
  });

  const barModelSelectGroups = useMemo(
    () => llmModelGroupsFromCatalog(llmCatalog?.models),
    [llmCatalog?.models],
  );

  const showBarModelPicker =
    apiReady &&
    !llmCatalogLoading &&
    (llmCatalog?.models?.length ?? 0) > 0;

  useEffect(() => {
    const list = llmCatalog?.models ?? [];
    const ids = new Set(list.map((m) => m.model_id));
    if (ids.size === 0) return;
    if (!ids.has(barModelId)) {
      setBarModelId(list[0]!.model_id);
    }
  }, [llmCatalog, barModelId]);

  const barChatModelReady = useMemo(() => {
    if (!showBarModelPicker) return false;
    return (llmCatalog?.models ?? []).some((m) => m.model_id === barModelId);
  }, [showBarModelPicker, llmCatalog?.models, barModelId]);

  const reportsLoading = !apiReady || reportsQueryLoading;
  const threadsLoading = !apiReady || threadsQueryLoading;

  const researchDockHeading = useMemo(() => {
    if (!researchDockReportId || !reportsData?.items?.length) return null;
    const r = reportsData.items.find((x) => x.id === researchDockReportId);
    return r?.title?.trim() || r?.query?.trim() || null;
  }, [researchDockReportId, reportsData?.items]);

  const barChatToggleLabel =
    barMode === "chat" && query.trim()
      ? truncateDisplayLabel(query.trim(), 28)
      : "Chat";
  const barResearchToggleLabel =
    barMode === "research" && query.trim()
      ? truncateDisplayLabel(query.trim(), 28)
      : "Research";

  const createJobMutation = useMutation({
    mutationFn: () =>
      jobsApi.create(
        query,
        barJobStrength,
        undefined,
        barDebugMockResearch,
        barModelId,
      ),
    onSuccess: (job) => {
      setDashThreadId(null);
      setDashLaunch(null);
      setQuery("");
      router.push(`/reports/${job.report_id}?job=${job.job_id}`);
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
      queryClient.invalidateQueries({ queryKey: ["report-default-thread"] });
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
          model_id: barModelId,
        });
        setQuery("");
        queryClient.invalidateQueries({ queryKey: ["dashboard-threads"] });
      } catch (err) {
        console.error("Failed to start chat thread", err);
      } finally {
        setDashChatBusy(false);
      }
    },
    [query, barMode, barExtended, barModelId, barJobStrength, createJobMutation, queryClient],
  );


  const handleCloseResearchDock = useCallback(() => {
    setResearchDockThreadId(null);
    setResearchDockReportId(null);
  }, []);

  const onLaunchConsumed = useCallback(() => {
    setDashLaunch(null);
  }, []);

  const handleCloseDashChat = useCallback(() => {
    setDashThreadId(null);
    setDashLaunch(null);
    queryClient.invalidateQueries({ queryKey: ["dashboard-threads"] });
  }, [queryClient]);

  const handleSelectSidebarThread = useCallback(
    (t: ThreadSummaryResponse) => {
      setDashLaunch(null);
      if (t.report_id) {
        router.push(`/reports/${t.report_id}?thread=${t.id}`);
        return;
      }
      setDashThreadId(t.id);
    },
    [router],
  );

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

  if (
    authStatus === "authenticated" &&
    (!session?.accessToken || session?.error)
  ) {
    return <AccountReconnectPrompt />;
  }

  const reports = reportsData?.items || [];

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden">
      <div className="flex min-h-0 flex-1 flex-row overflow-hidden">
        <ChatHistorySidebar
          collapsed={chatSidebarCollapsed}
          onToggleCollapsed={() => setChatSidebarCollapsed((c) => !c)}
          threads={threadsRaw ?? []}
          selectedThreadId={dashThreadId}
          onSelectThread={handleSelectSidebarThread}
          onNewChat={handleSidebarNewChat}
          onRequestDelete={setDeleteThreadTarget}
          isLoading={threadsLoading}
        />

        <main className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-visible bg-[var(--rpt-bg)]">
          {dashThreadId ? (
            <ChatPanel
              key={dashThreadId}
              threadId={dashThreadId}
              placement="main"
              launchWith={dashLaunch}
              onLaunchConsumed={onLaunchConsumed}
              onClose={handleCloseDashChat}
              initialModelId={barModelId}
            />
          ) : (
            <div className="flex min-h-0 w-full min-w-0 flex-1 flex-col overflow-hidden">
              <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain px-6 pb-6 pt-28">
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

              {reportsLoading ? (
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
              <div className="shrink-0 border-t border-[#e5e2db] bg-[rgba(255,255,255,0.92)] px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-sm sm:px-6">
        <form
          onSubmit={handleBarSubmit}
          className="w-full rounded-2xl border border-[#e5e2db] bg-[rgba(255,255,255,0.85)] p-2.5"
        >
          <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-2">
            <div className="inline-flex shrink-0 gap-0.5 rounded-lg bg-neutral-100/80 p-0.5">
              <button
                type="button"
                onClick={() => setBarMode("chat")}
                title={barMode === "chat" && query.trim() ? query.trim() : "Chat"}
                className={cn(
                  "max-w-[min(11rem,40vw)] truncate rounded-md px-2.5 py-1 text-xs font-medium text-neutral-600 transition-colors",
                  barMode === "chat" && "bg-white text-neutral-900 shadow-sm",
                )}
              >
                {barChatToggleLabel}
              </button>
              <button
                type="button"
                onClick={() => setBarMode("research")}
                title={
                  barMode === "research" && query.trim()
                    ? query.trim()
                    : "Research"
                }
                className={cn(
                  "max-w-[min(11rem,40vw)] truncate rounded-md px-2.5 py-1 text-xs font-medium text-neutral-600 transition-colors",
                  barMode === "research" && "bg-white text-neutral-900 shadow-sm",
                )}
              >
                {barResearchToggleLabel}
              </button>
            </div>

            {showBarModelPicker ? (
              <div className="flex min-w-0 max-w-full flex-[1_1_12rem] items-start gap-2 sm:items-center">
                <span className="shrink-0 pt-1.5 text-xs text-neutral-500 sm:pt-0">Model</span>
                <ChatModelPicker
                  groups={barModelSelectGroups}
                  value={barModelId}
                  disabled={dashChatBusy || createJobMutation.isPending}
                  onChange={setBarModelId}
                />
              </div>
            ) : null}

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
              <div className="flex min-w-0 flex-1 basis-[min(100%,14rem)] flex-wrap items-center gap-2 sm:basis-auto sm:max-w-md">
                <span className="shrink-0 text-xs text-neutral-500">Intensity</span>
                <div className="flex shrink-0 items-center gap-0.5 rounded-lg bg-neutral-100/90 p-0.5">
                  {RESEARCH_INTENSITY_OPTIONS.map(({ tier, label }) => (
                    <button
                      key={tier}
                      type="button"
                      disabled={dashChatBusy || createJobMutation.isPending}
                      onClick={() => setBarJobStrength(tier)}
                      className={cn(
                        "rounded-md px-2 py-1 text-xs font-medium transition-colors disabled:opacity-40",
                        barJobStrength === tier
                          ? "bg-neutral-800 text-white shadow-sm"
                          : "text-neutral-600 hover:bg-white/80",
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {showDebugMockResearchControls(session?.user?.email) ? (
                  <label className="ml-1 flex shrink-0 cursor-pointer items-center gap-1.5 text-xs text-amber-900/90">
                    <input
                      type="checkbox"
                      checked={barDebugMockResearch}
                      onChange={(e) => setBarDebugMockResearch(e.target.checked)}
                      className="rounded border-amber-500 text-amber-700"
                    />
                    Mock (no LLM)
                  </label>
                ) : null}
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
                (barMode === "research" && query.trim().length < 10) ||
                ((barMode === "chat" || barMode === "research") &&
                  showBarModelPicker &&
                  !barChatModelReady)
              }
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white transition-opacity",
                query.trim() &&
                  !createJobMutation.isPending &&
                  !dashChatBusy &&
                  !(barMode === "research" && query.trim().length < 10) &&
                  !(
                    (barMode === "chat" || barMode === "research") &&
                    showBarModelPicker &&
                    !barChatModelReady
                  )
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
            </div>
          )}
          <DashboardMainFloatingChrome
            onBackToProjects={
              dashThreadId ? handleCloseDashChat : undefined
            }
          />
        </main>

        <AnimatePresence>
          {researchDockThreadId ? (
            <ChatPanel
              key={researchDockThreadId}
              threadId={researchDockThreadId}
              placement="dock"
              reportScope
              reportHeading={researchDockHeading}
              onClose={handleCloseResearchDock}
            />
          ) : null}
        </AnimatePresence>
      </div>

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
