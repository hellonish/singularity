"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { X, Send, Loader2 } from "lucide-react";
import { getSession } from "next-auth/react";
import { threadsApi, type MessageResponse } from "@/lib/api";
import { cn } from "@/lib/cn";
import { MessageBubble } from "./MessageBubble";
import { StreamingMessage } from "./StreamingMessage";

/** Dedupes bootstrap sends across React Strict Mode double effect runs. */
const launchedBootstrapKeys = new Set<string>();

type ExecutionMode = "chat" | "research";

export type ChatPanelLaunchPayload = {
  nonce: number;
  message: string;
  execution_mode: ExecutionMode;
  chat_variant: "standard" | "extended";
  research_strength: number;
};

type SendOverrides = {
  content: string;
  execution_mode: ExecutionMode;
  chat_variant: "standard" | "extended";
  research_strength: number;
  onComplete?: () => void;
};

interface ChatPanelProps {
  threadId: string;
  reportContent?: string;
  /** When true, show report-scoped labels even if report markdown is not loaded (e.g. dashboard research dock). */
  reportScope?: boolean;
  onClose: () => void;
  /** overlay = report page right rail; dock = legacy narrow column; main = dashboard primary column */
  placement?: "overlay" | "dock" | "main";
  launchWith?: ChatPanelLaunchPayload | null;
  onLaunchConsumed?: () => void;
}

/**
 * Purpose: Thread UI with pill composer (chat vs research, extended, intensity) and optional
 * bootstrap of the first turn when opened from the dashboard bar.
 */
export function ChatPanel({
  threadId,
  reportContent,
  reportScope = false,
  onClose,
  placement = "overlay",
  launchWith,
  onLaunchConsumed,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingTokens, setStreamingTokens] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("chat");
  const [extendedOn, setExtendedOn] = useState(false);
  const [researchStrength, setResearchStrength] = useState(5);
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const chatVariant = extendedOn ? "extended" : "standard";
  const standalone = !reportContent && !reportScope;

  useEffect(() => {
    threadsApi
      .get(threadId)
      .then((data) => {
        setMessages(data.messages);
      })
      .catch((e) => {
        console.error("Failed to load thread messages", e);
      });
  }, [threadId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingTokens]);

  const runSend = useCallback(
    async (overrides?: SendOverrides) => {
      const content = (overrides?.content ?? input).trim();
      if (!content || streaming) return;
      const execMode = overrides?.execution_mode ?? executionMode;
      const variant = overrides?.chat_variant ?? chatVariant;
      const strength = overrides?.research_strength ?? researchStrength;
      if (!overrides) setInput("");
      setStreaming(true);
      setStreamingTokens("");
      setError(null);
      setStatusLine(
        execMode === "research" ? `Running research (intensity ${strength}/10)…` : null,
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
          }),
        });

        if (!res.ok || !res.body) {
          throw new Error(`Request failed: ${res.status}`);
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
                    setStatusLine(`Research · intensity ${p.strength}/10`);
                  } else if (p.mode === "chat") {
                    setStatusLine("Chat mode");
                  }
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
    ],
  );

  useEffect(() => {
    if (!launchWith) return;
    const key = `${threadId}:${launchWith.nonce}`;
    if (launchedBootstrapKeys.has(key)) return;
    launchedBootstrapKeys.add(key);
    setExecutionMode(launchWith.execution_mode);
    setExtendedOn(launchWith.chat_variant === "extended");
    setResearchStrength(launchWith.research_strength);
    void runSend({
      content: launchWith.message,
      execution_mode: launchWith.execution_mode,
      chat_variant: launchWith.chat_variant,
      research_strength: launchWith.research_strength,
      onComplete: () => onLaunchConsumed?.(),
    });
  }, [launchWith, threadId, runSend, onLaunchConsumed]);

  const sendMessage = useCallback(() => {
    void runSend();
  }, [runSend]);

  const shellClass =
    placement === "overlay"
      ? "fixed right-0 top-14 z-[60] flex min-h-0 w-[min(100vw,380px)] flex-col overflow-hidden border-l border-neutral-200/80 bg-white"
      : placement === "main"
        ? "flex min-h-0 h-full max-h-full w-full min-w-0 flex-1 flex-col overflow-hidden bg-[#f8fafc]"
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
        {placement === "main" ? (
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          >
            ← Projects
          </button>
        ) : (
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-800"
            aria-label="Close chat"
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        )}
      </div>

      <div
        className={cn(
          "min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain py-4",
          placement === "main" ? "w-full px-4 md:px-8" : "px-4",
        )}
        style={{ scrollbarWidth: "thin" }}
      >
        {messages.length === 0 && !streaming ? (
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
          placement === "main" ? "w-full px-4 md:px-8" : "px-3",
        )}
      >
        <div className="rounded-2xl border border-neutral-200/90 bg-neutral-50/50 p-2.5">
          <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-2">
            <div className="inline-flex shrink-0 gap-0.5 rounded-lg bg-neutral-100/80 p-0.5">
              <button
                type="button"
                disabled={streaming}
                onClick={() => setExecutionMode("chat")}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium text-neutral-600 transition-colors disabled:opacity-40",
                  executionMode === "chat" && "bg-white text-neutral-900 shadow-sm",
                )}
              >
                Chat
              </button>
              <button
                type="button"
                disabled={streaming}
                onClick={() => setExecutionMode("research")}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium text-neutral-600 transition-colors disabled:opacity-40",
                  executionMode === "research" && "bg-white text-neutral-900 shadow-sm",
                )}
              >
                Research
              </button>
            </div>

            {executionMode === "chat" ? (
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
              <div className="flex min-w-0 flex-1 basis-[min(100%,11rem)] items-center gap-2">
                <span className="shrink-0 text-xs text-neutral-500">Intensity</span>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={researchStrength}
                  disabled={streaming}
                  onChange={(e) => setResearchStrength(Number(e.target.value))}
                  className="min-w-0 flex-1 accent-neutral-700"
                />
                <span className="w-4 shrink-0 text-right text-xs tabular-nums text-neutral-600">
                  {researchStrength}
                </span>
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
              disabled={!input.trim() || streaming}
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
