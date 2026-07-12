"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { X, Send, Loader2 } from "lucide-react";
import { getSession, useSession } from "next-auth/react";
import {
  threadsApi,
  llmApi,
  DEFAULT_CHAT_MODEL_ID,
  type MessageResponse,
} from "@/lib/api";
import { cn } from "@/lib/cn";
import { llmModelGroupsFromCatalog } from "@/lib/llm_model_groups";
import {
  truncateDisplayLabel,
  researchIntensityLabel,
  RESEARCH_INTENSITY_OPTIONS,
  clampResearchIntensityTier,
} from "@/lib/utils";
import { ChatModelPicker } from "./ChatModelPicker";
import { MessageBubble } from "./MessageBubble";
import { StreamingMessage } from "./StreamingMessage";

/** Dedupes bootstrap sends across React Strict Mode double effect runs. */
const launchedBootstrapKeys = new Set<string>();

/** Matches split-pane surface (`bg-white`) for a soft radial scrim behind floating chrome. */
const SPLIT_PANE_SCRIM_RGB = "255,255,255";

type ExecutionMode = "chat" | "research";

export type ChatPanelLaunchPayload = {
  nonce: number;
  message: string;
  execution_mode: ExecutionMode;
  chat_variant: "standard" | "extended";
  research_strength: number;
  /** When set (e.g. from dashboard bar), used for the bootstrap send model_id. */
  model_id?: string;
};

type SendOverrides = {
  content: string;
  execution_mode: ExecutionMode;
  chat_variant: "standard" | "extended";
  research_strength: number;
  model_id?: string;
  onComplete?: () => void;
};

interface ChatPanelProps {
  threadId: string;
  reportContent?: string;
  /** When true, show report-scoped labels even if report markdown is not loaded (e.g. dashboard research dock). */
  reportScope?: boolean;
  /** Report title (or primary heading) for pane labels when this thread is tied to a report. */
  reportHeading?: string | null;
  onClose: () => void;
  /** overlay = report page slide-over; dock = dashboard right rail; main = dashboard primary; split = report page two-column */
  placement?: "overlay" | "dock" | "main" | "split";
  launchWith?: ChatPanelLaunchPayload | null;
  onLaunchConsumed?: () => void;
  /** Seeds the response model when the panel mounts (e.g. dashboard bar selection). */
  initialModelId?: string | null;
}

/**
 * Purpose: Thread UI with pill composer (chat vs research, extended, intensity) and optional
 * bootstrap of the first turn when opened from the dashboard bar.
 */
export function ChatPanel({
  threadId,
  reportContent,
  reportScope = false,
  reportHeading = null,
  onClose,
  placement = "overlay",
  launchWith,
  onLaunchConsumed,
  initialModelId = null,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingTokens, setStreamingTokens] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("chat");
  const [extendedOn, setExtendedOn] = useState(false);
  const [researchStrength, setResearchStrength] = useState<1 | 2 | 3>(2);
  const [selectedModelId, setSelectedModelId] = useState(
    () => initialModelId?.trim() || DEFAULT_CHAT_MODEL_ID,
  );
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const chatVariant = extendedOn ? "extended" : "standard";
  const standalone = !reportContent && !reportScope;
  /** Report Q&A follow-ups: chat agent only (no research runs from this thread). */
  const followUpChatOnly = !standalone;

  const firstUserPaneLabel = useMemo(() => {
    const m = messages.find((x) => x.role === "user");
    return m ? truncateDisplayLabel(m.content, 40) : "";
  }, [messages]);

  const reportPaneLabel = useMemo(() => {
    if (standalone) return "";
    const h = reportHeading?.trim();
    return h ? truncateDisplayLabel(h, 40) : "";
  }, [standalone, reportHeading]);

  const headerTitle = standalone
    ? firstUserPaneLabel || "Chat"
    : reportPaneLabel || firstUserPaneLabel || "Report";

  const chatToggleLabel = firstUserPaneLabel || "Chat";
  const researchToggleLabel = standalone
    ? "Research"
    : reportPaneLabel || "Research";

  const { data: session, status: sessionStatus } = useSession();
  const accessReady =
    sessionStatus === "authenticated" && Boolean(session?.accessToken);

  const { data: llmCatalog, isLoading: llmCatalogLoading } = useQuery({
    queryKey: ["llm-catalog"],
    queryFn: () => llmApi.models(),
    enabled: accessReady,
    staleTime: 120_000,
  });

  const showModelPicker =
    accessReady &&
    !llmCatalogLoading &&
    (llmCatalog?.models?.length ?? 0) > 0;

  const hasSelectableModel = useMemo(() => {
    if (!showModelPicker) return false;
    const list = llmCatalog?.models ?? [];
    return list.some((m) => m.model_id === selectedModelId);
  }, [showModelPicker, llmCatalog?.models, selectedModelId]);

  const modelSelectGroups = useMemo(
    () => llmModelGroupsFromCatalog(llmCatalog?.models),
    [llmCatalog?.models],
  );

  useEffect(() => {
    const list = llmCatalog?.models ?? [];
    const ids = new Set(list.map((m) => m.model_id));
    if (ids.size === 0) return;
    if (!ids.has(selectedModelId)) {
      setSelectedModelId(list[0]!.model_id);
    }
  }, [llmCatalog, selectedModelId]);

  useEffect(() => {
    const pref = initialModelId?.trim();
    if (!pref) return;
    const list = llmCatalog?.models ?? [];
    if (list.some((m) => m.model_id === pref)) {
      setSelectedModelId(pref);
    }
  }, [initialModelId, llmCatalog?.models]);

  useEffect(() => {
    if (!threadId || !accessReady) return;
    let cancelled = false;
    threadsApi
      .get(threadId)
      .then((data) => {
        if (cancelled) return;
        setMessages(data.messages);
      })
      .catch((e) => {
        if (!cancelled) console.error("Failed to load thread messages", e);
      });
    return () => {
      cancelled = true;
    };
  }, [threadId, accessReady]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingTokens]);

  useEffect(() => {
    if (followUpChatOnly) setExecutionMode("chat");
  }, [followUpChatOnly, threadId]);

  const runSend = useCallback(
    async (overrides?: SendOverrides) => {
      const content = (overrides?.content ?? input).trim();
      const catalogIds = new Set((llmCatalog?.models ?? []).map((m) => m.model_id));
      if (!content || streaming) return;
      if (
        !accessReady ||
        llmCatalogLoading ||
        catalogIds.size === 0 ||
        !catalogIds.has(selectedModelId)
      ) {
        return;
      }
      const execMode = followUpChatOnly
        ? "chat"
        : overrides?.execution_mode ?? executionMode;
      const variant = overrides?.chat_variant ?? chatVariant;
      const strength = clampResearchIntensityTier(
        overrides?.research_strength ?? researchStrength,
      );
      const modelId = overrides?.model_id ?? selectedModelId;
      if (!overrides) setInput("");
      setStreaming(true);
      setStreamingTokens("");
      setError(null);
      setStatusLine(
        execMode === "research"
          ? `Running research (${researchIntensityLabel(strength)} intensity)…`
          : null,
      );

      const userMsg: MessageResponse = {
        id: `tmp-${Date.now()}`,
        role: "user",
        content,
        token_count: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        const session = await getSession();
        const token = (session as any)?.accessToken;
        const url = threadsApi.sendMessageUrl(threadId);

        const res = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            content,
            execution_mode: execMode,
            chat_variant: variant,
            research_strength: strength,
            model_id: modelId,
          }),
        });

        if (!res.ok || !res.body) {
          const errText = await res.text();
          let msg = `Request failed: ${res.status}`;
          try {
            const j = JSON.parse(errText) as { detail?: unknown };
            if (typeof j.detail === "string") msg = j.detail;
          } catch {
            /* ignore */
          }
          throw new Error(msg);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let currentEvent = "message";
        let accumulated = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const raw = line.slice(6);
              if (!raw.trim()) continue;
              try {
                const parsed: unknown = JSON.parse(raw);
                if (currentEvent === "token") {
                  const o = parsed as { token?: string; text?: string };
                  const piece = o.token ?? o.text ?? "";
                  if (piece) {
                    accumulated += piece;
                    setStreamingTokens(accumulated);
                  }
                } else if (currentEvent === "plan") {
                  const p = parsed as { mode?: string; strength?: number };
                  if (p.mode === "research" && typeof p.strength === "number") {
                    setStatusLine(
                      `Research · ${researchIntensityLabel(p.strength)} intensity`,
                    );
                  } else if (p.mode === "chat") {
                    setStatusLine("Chat mode");
                  }
                } else if (currentEvent === "step") {
                  const s = parsed as {
                    step_id?: number;
                    step_type?: string;
                    description?: string;
                  };
                  const label =
                    s.description != null && String(s.description).trim()
                      ? `Step ${s.step_id ?? "?"}: ${s.description}`
                      : `Step ${s.step_id ?? "?"} (${s.step_type ?? "?"})`;
                  setStatusLine(label);
                } else if (currentEvent === "done") {
                  const d = parsed as { message_id?: string; token_count?: number | null };
                  const doneMsg: MessageResponse = {
                    id: d.message_id || `assistant-${Date.now()}`,
                    role: "assistant",
                    content: accumulated,
                    token_count: d.token_count ?? null,
                    created_at: new Date().toISOString(),
                  };
                  setMessages((prev) => [...prev, doneMsg]);
                  setStreamingTokens("");
                  accumulated = "";
                } else if (currentEvent === "error") {
                  const err = parsed as { message?: string };
                  setError(err.message || "Response error");
                }
              } catch {
                // Ignore non-JSON data lines
              }
            }
          }
        }
      } catch (e: any) {
        setError(e?.message || "Connection failed");
      } finally {
        setStreaming(false);
        setStreamingTokens("");
        setStatusLine(null);
        overrides?.onComplete?.();
      }
    },
    [
      input,
      streaming,
      threadId,
      executionMode,
      chatVariant,
      researchStrength,
      followUpChatOnly,
      selectedModelId,
      llmCatalog?.models,
      accessReady,
      llmCatalogLoading,
    ],
  );

  useEffect(() => {
    if (!launchWith || !accessReady) return;
    if (llmCatalogLoading) return;
    const list = llmCatalog?.models ?? [];
    const bootKey = `${threadId}:${launchWith.nonce}`;
    if (list.length === 0) {
      if (!launchedBootstrapKeys.has(bootKey)) {
        launchedBootstrapKeys.add(bootKey);
        onLaunchConsumed?.();
      }
      return;
    }
    if (launchedBootstrapKeys.has(bootKey)) return;
    launchedBootstrapKeys.add(bootKey);
    const bootMode = followUpChatOnly ? "chat" : launchWith.execution_mode;
    setExecutionMode(bootMode);
    setExtendedOn(launchWith.chat_variant === "extended");
    setResearchStrength(clampResearchIntensityTier(launchWith.research_strength));
    const fromLaunch = launchWith.model_id?.trim();
    const mid =
      fromLaunch && list.some((m) => m.model_id === fromLaunch)
        ? fromLaunch
        : list.some((m) => m.model_id === selectedModelId)
          ? selectedModelId
          : list[0]!.model_id;
    void runSend({
      content: launchWith.message,
      execution_mode: bootMode,
      chat_variant: launchWith.chat_variant,
      research_strength: launchWith.research_strength,
      model_id: mid,
      onComplete: () => onLaunchConsumed?.(),
    });
  }, [
    launchWith,
    threadId,
    runSend,
    onLaunchConsumed,
    accessReady,
    followUpChatOnly,
    selectedModelId,
    llmCatalogLoading,
    llmCatalog?.models,
  ]);

  const sendMessage = useCallback(() => {
    void runSend();
  }, [runSend]);

  const shellClass =
    placement === "overlay"
      ? "fixed right-0 top-14 z-[60] flex min-h-0 w-[min(100vw,380px)] flex-col overflow-hidden border-l border-neutral-200/80 bg-white"
      : placement === "main"
        ? "flex min-h-0 h-full max-h-full w-full min-w-0 flex-1 flex-col overflow-hidden bg-[var(--rpt-bg)]"
        : placement === "split"
          ? "relative flex h-full min-h-0 w-full min-w-0 flex-col overflow-hidden bg-white"
          : "flex h-full min-h-0 w-[min(100vw,380px)] shrink-0 flex-col overflow-hidden border-l border-neutral-200/80 bg-white";

  const shellStyle =
    placement === "overlay"
      ? {
          height: "calc(100dvh - 3.5rem)",
          maxHeight: "calc(100dvh - 3.5rem)",
        }
      : undefined;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className={shellClass}
      style={shellStyle}
    >
      {placement === "split" ? (
        <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex h-[6.75rem] justify-start">
          <div
            className="absolute left-0 top-0 h-full w-[min(100%,17rem)]"
            aria-hidden
            style={{
              background: `radial-gradient(ellipse 100% 115% at 0% 0%, rgb(${SPLIT_PANE_SCRIM_RGB}) 0%, rgb(${SPLIT_PANE_SCRIM_RGB}) 32%, rgba(${SPLIT_PANE_SCRIM_RGB},0.97) 48%, rgba(${SPLIT_PANE_SCRIM_RGB},0.82) 62%, rgba(${SPLIT_PANE_SCRIM_RGB},0.38) 80%, rgba(${SPLIT_PANE_SCRIM_RGB},0.08) 92%, rgba(${SPLIT_PANE_SCRIM_RGB},0) 100%)`,
            }}
          />
          <div className="pointer-events-auto relative z-10 px-4 pt-3">
            <p className="text-sm font-medium text-neutral-800">Report chat</p>
            <p className="text-xs text-neutral-500">Includes this report</p>
            {statusLine ? (
              <p className="mt-1 text-xs text-neutral-500">{statusLine}</p>
            ) : null}
          </div>
        </div>
      ) : placement === "overlay" || placement === "dock" ? (
        <div className="flex flex-shrink-0 items-center justify-between border-b border-neutral-200/80 bg-white/90 px-4 py-2.5 backdrop-blur-sm">
          <div>
            <p className="text-sm font-medium text-neutral-800">
              {standalone ? "Chat" : "Report chat"}
            </p>
            {!standalone ? (
              <p className="text-xs text-neutral-500">Includes this report</p>
            ) : null}
            {statusLine ? (
              <p className="mt-0.5 text-xs text-neutral-500">{statusLine}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-800"
            aria-label="Close chat"
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>
      ) : null}

      <div
        className={cn(
          "min-h-0 min-w-0 flex-1 space-y-4 overflow-x-auto overflow-y-auto overscroll-contain",
          placement === "main"
            ? "w-full px-4 pb-4 pt-28 md:px-8"
            : placement === "split"
              ? "w-full px-4 pb-4 pt-[5.75rem] md:px-8"
              : "px-4 py-4",
        )}
        style={{ scrollbarWidth: "thin" }}
      >
        {placement === "main" && statusLine ? (
          <div
            className="sticky top-0 z-[1] -mt-2 mb-1 border-b border-[#e5e2db] bg-[var(--rpt-bg)]/95 py-2 text-xs text-[var(--rpt-text-dim)] backdrop-blur-sm"
            role="status"
          >
            {statusLine}
          </div>
        ) : null}
        {!accessReady && threadId ? (
          <div className="flex h-28 flex-col items-center justify-center gap-2 px-4">
            <Loader2 size={18} className="animate-spin text-neutral-400" />
            <p className="text-center text-sm text-neutral-500">Loading conversation…</p>
          </div>
        ) : messages.length === 0 && !streaming ? (
          <div className="flex h-28 items-center justify-center px-4">
            <p className="text-center text-sm leading-relaxed text-neutral-400">
              {standalone
                ? "Continue the conversation below."
                : "Ask a question about this report."}
            </p>
          </div>
        ) : null}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {streaming && streamingTokens ? (
          <StreamingMessage content={streamingTokens} />
        ) : null}
        {streaming && !streamingTokens ? (
          <div className="flex items-center gap-2 px-3 py-2">
            <Loader2 size={14} className="animate-spin text-neutral-400" />
            <span className="text-xs text-neutral-500">Thinking…</span>
          </div>
        ) : null}
        {error ? (
          <p
            style={{
              fontFamily: "var(--mono)",
              fontSize: 11,
              color: "#dc2626",
              padding: "8px 12px",
            }}
          >
            {error}
          </p>
        ) : null}
        <div ref={bottomRef} />
      </div>

      <div
        className={cn(
          "flex-shrink-0 border-t border-neutral-200/80 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2",
          placement === "main" || placement === "split"
            ? "w-full px-4 md:px-8"
            : "px-3",
        )}
      >
        <div className="rounded-2xl border border-neutral-200/90 bg-neutral-50/50 p-2.5">
          <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-2">
            {!followUpChatOnly ? (
              <div className="inline-flex shrink-0 gap-0.5 rounded-lg bg-neutral-100/80 p-0.5">
                <button
                  type="button"
                  disabled={streaming}
                  onClick={() => setExecutionMode("chat")}
                  title={firstUserPaneLabel || "Chat"}
                  className={cn(
                    "max-w-[min(12rem,42vw)] truncate rounded-md px-2.5 py-1 text-xs font-medium text-neutral-600 transition-colors disabled:opacity-40",
                    executionMode === "chat" && "bg-white text-neutral-900 shadow-sm",
                  )}
                >
                  {chatToggleLabel}
                </button>
                <button
                  type="button"
                  disabled={streaming}
                  onClick={() => setExecutionMode("research")}
                  title={
                    standalone
                      ? "Research"
                      : reportHeading?.trim() || "Research"
                  }
                  className={cn(
                    "max-w-[min(12rem,42vw)] truncate rounded-md px-2.5 py-1 text-xs font-medium text-neutral-600 transition-colors disabled:opacity-40",
                    executionMode === "research" && "bg-white text-neutral-900 shadow-sm",
                  )}
                >
                  {researchToggleLabel}
                </button>
              </div>
            ) : null}

            {showModelPicker ? (
              <div className="flex min-w-0 max-w-full flex-[1_1_14rem] items-start gap-2 sm:items-center">
                <span className="shrink-0 pt-1.5 text-xs text-neutral-500 sm:pt-0">Model</span>
                <ChatModelPicker
                  groups={modelSelectGroups}
                  value={selectedModelId}
                  disabled={streaming}
                  onChange={setSelectedModelId}
                />
              </div>
            ) : null}

            {followUpChatOnly || executionMode === "chat" ? (
              <div className="flex shrink-0 items-center gap-2">
                <span className="text-xs text-neutral-500">Extended</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={extendedOn}
                  disabled={streaming}
                  onClick={() => setExtendedOn((v) => !v)}
                  className={cn(
                    "relative h-6 w-10 shrink-0 rounded-full p-px transition-colors disabled:opacity-40",
                    extendedOn ? "bg-neutral-800" : "bg-neutral-300",
                  )}
                >
                  <span
                    className={cn(
                      "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-[left,right] duration-200 ease-out",
                      extendedOn
                        ? "left-auto right-px"
                        : "left-px right-auto",
                    )}
                  />
                </button>
              </div>
            ) : (
              <div className="flex min-w-0 flex-1 basis-[min(100%,11rem)] flex-wrap items-center gap-2">
                <span className="shrink-0 text-xs text-neutral-500">Intensity</span>
                <div className="flex shrink-0 items-center gap-0.5 rounded-lg bg-neutral-100/90 p-0.5">
                  {RESEARCH_INTENSITY_OPTIONS.map(({ tier, label }) => (
                    <button
                      key={tier}
                      type="button"
                      disabled={streaming}
                      onClick={() => setResearchStrength(tier)}
                      className={cn(
                        "rounded-md px-2 py-1 text-xs font-medium transition-colors disabled:opacity-40",
                        researchStrength === tier
                          ? "bg-neutral-800 text-white shadow-sm"
                          : "text-neutral-600 hover:bg-white/80",
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex items-end gap-2 rounded-xl border border-neutral-200 bg-white px-2 py-1.5">
            <textarea
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Message…"
              disabled={streaming}
              className="max-h-[120px] min-h-[36px] flex-1 resize-none bg-transparent py-2 pl-2 pr-1 text-sm text-neutral-900 outline-none placeholder:text-neutral-400"
              style={{
                lineHeight: 1.45,
                fontFamily: "var(--serif, 'Newsreader', Georgia, serif)",
              }}
              rows={1}
            />
            <button
              type="button"
              onClick={sendMessage}
              disabled={!input.trim() || streaming || !hasSelectableModel}
              className={cn(
                "mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white transition-opacity",
                input.trim() && !streaming
                  ? "bg-neutral-900 hover:bg-neutral-800"
                  : "bg-neutral-200 text-neutral-400",
              )}
              aria-label="Send"
            >
              <Send size={14} strokeWidth={2} />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
