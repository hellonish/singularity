"use client";

import "@/styles/report-content.css";
import "katex/dist/katex.min.css";

import { useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Download, MessageSquare } from "lucide-react";
import { reportsApi, threadsApi, ApiError } from "@/lib/api";
import { ReportViewer, type TOCEntry } from "@/components/report/ReportViewer";
import { ReportTOC } from "@/components/report/ReportTOC";
import { SelectionToolbar } from "@/components/report/SelectionToolbar";
import { PatchModal } from "@/components/report/PatchModal";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { UserMenu } from "@/components/user-menu";

export default function ReportViewPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const reportId = params.id as string;

  const [tocEntries, setTocEntries] = useState<TOCEntry[]>([]);
  const [chatOpen, setChatOpen] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [selectedText, setSelectedText] = useState("");
  const [selectedHeadingSlug, setSelectedHeadingSlug] = useState<string | null>(null);
  const [patchModalOpen, setPatchModalOpen] = useState(false);
  const [patchConflict, setPatchConflict] = useState(false);

  const { data: reportMeta, isLoading: metaLoading, isFetching: metaFetching } = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => reportsApi.get(reportId),
    enabled: !!reportId,
    refetchInterval: (query) => {
      const d = query.state.data;
      if (!d || d.latest_version != null) return false;
      return 4000;
    },
  });

  const { data: versionContent, isLoading: contentLoading } = useQuery({
    queryKey: ["report-content", reportId, reportMeta?.latest_version],
    queryFn: () => reportsApi.getVersionContent(reportId, reportMeta!.latest_version!),
    enabled: !!reportMeta?.latest_version,
  });

  const { data: versionsData } = useQuery({
    queryKey: ["report-versions", reportId],
    queryFn: () => reportsApi.getVersions(reportId),
    enabled: !!reportId,
  });

  const isLoading = metaLoading || contentLoading;
  const isEditable = !!versionContent && !isLoading;

  const handleOpenChat = useCallback(async () => {
    if (!threadId) {
      try {
        const thread = await threadsApi.create(reportId, versionContent?.version_num);
        setThreadId(thread.id);
      } catch (e) {
        console.error("Failed to create thread", e);
        return;
      }
    }
    setChatOpen(true);
  }, [threadId, reportId, versionContent?.version_num]);

  const handleSelection = useCallback((text: string, headingSlug: string | null) => {
    setSelectedText(text);
    setSelectedHeadingSlug(headingSlug);
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

  return (
    <div className="min-h-screen" style={{ background: "var(--rpt-bg)" }}>
      {/* ── Fixed light header ── */}
      <header
        className="fixed top-0 left-0 right-0 z-40 flex items-center gap-3 px-5 h-14"
        style={{
          background: "rgba(255,255,255,0.95)",
          borderBottom: "1px solid #e5e2db",
          backdropFilter: "blur(8px)",
        }}
      >
        <button
          onClick={() => router.push("/dashboard")}
          className="flex items-center gap-1.5 transition-colors flex-shrink-0"
          style={{ color: "#6b7280", fontFamily: "var(--mono)", fontSize: 12 }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#1a1a1a")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#6b7280")}
        >
          <ArrowLeft size={14} />
          Dashboard
        </button>

        <div className="flex-1 min-w-0">
          {reportMeta && (
            <p
              className="truncate"
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

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Version badge */}
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

          {/* Export */}
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

          {/* Chat toggle */}
          <button
            type="button"
            title={chatOpen ? "Close Q&A panel" : "Open Q&A chat (choose Chat or Research mode in the panel)"}
            onClick={chatOpen ? () => setChatOpen(false) : handleOpenChat}
            className="flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
            style={{
              fontFamily: "var(--mono)",
              background: chatOpen ? "rgba(99,102,241,0.1)" : "#f3f4f6",
              border: `1px solid ${chatOpen ? "#6366f1" : "#e5e2db"}`,
              color: chatOpen ? "#4f46e5" : "#6b7280",
            }}
          >
            <MessageSquare size={13} />
            Q&amp;A
          </button>

          <UserMenu />
        </div>
      </header>

      {/* ── Conflict banner ── */}
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

      {/* ── Main body ── */}
      <div className="flex min-h-screen pt-14">
        {/* Report area */}
        <div
          className="flex-1 overflow-y-auto transition-all duration-300"
          style={{ marginRight: chatOpen ? "min(380px, 100vw)" : 0 }}
        >
          {isLoading ? (
            <LoadingSkeleton />
          ) : versionContent ? (
            <div className="report-page-layout" style={{ position: "relative" }}>
              {/* TOC sidebar */}
              <ReportTOC entries={tocEntries} />

              {/* Report content column */}
              <div>
                {/* Report header */}
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
                      <span>Strength {reportMeta.strength}/10</span>
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

                {/* Viewer with floating selection toolbar */}
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

        {/* Chat panel — slide in from right */}
        <AnimatePresence>
          {chatOpen && threadId && (
            <ChatPanel
              threadId={threadId}
              reportContent={versionContent?.content}
              placement="overlay"
              onClose={() => setChatOpen(false)}
            />
          )}
        </AnimatePresence>
      </div>

      {/* Patch modal */}
      <PatchModal
        open={patchModalOpen}
        selectedText={selectedText}
        onClose={() => setPatchModalOpen(false)}
        onSubmit={handlePatch}
      />
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
