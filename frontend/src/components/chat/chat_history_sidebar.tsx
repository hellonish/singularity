"use client";

import { ChevronLeft, ChevronRight, MessageSquare, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/cn";
import type { ThreadResponse } from "@/lib/api";

export interface ChatHistorySidebarProps {
  /** When true, only the narrow rail with expand control is shown. */
  collapsed: boolean;
  onToggleCollapsed: () => void;
  /** Standalone dashboard threads (no linked report). */
  threads: ThreadResponse[];
  selectedThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  /** Clear selection and return main area to the reports list. */
  onNewChat: () => void;
  /** Opens delete confirmation (same pattern as report cards). */
  onRequestDelete: (thread: ThreadResponse) => void;
  isLoading: boolean;
}

/**
 * Purpose: Collapsible left rail listing standalone chat threads (dashboard).
 * Inputs: thread list, selection, collapse state, callbacks.
 * Outputs: Renders sidebar UI; selection drives main-area ChatPanel via parent.
 */
export function ChatHistorySidebar({
  collapsed,
  onToggleCollapsed,
  threads,
  selectedThreadId,
  onSelectThread,
  onNewChat,
  onRequestDelete,
  isLoading,
}: ChatHistorySidebarProps) {
  return (
    <aside
      className={cn(
        "flex min-h-0 shrink-0 flex-col self-stretch border-r border-neutral-200/80 bg-white transition-[width] duration-200 ease-out",
        collapsed ? "w-[52px]" : "w-[min(100vw,260px)]",
      )}
      aria-label="Chat history"
    >
      <div className="flex h-12 shrink-0 items-center gap-1 border-b border-neutral-200/80 px-2">
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand chat history" : "Collapse chat history"}
        >
          {collapsed ? (
            <ChevronRight className="h-5 w-5" strokeWidth={1.75} />
          ) : (
            <ChevronLeft className="h-5 w-5" strokeWidth={1.75} />
          )}
        </button>
        {!collapsed ? (
          <span className="min-w-0 flex-1 truncate text-sm font-semibold text-neutral-800">
            Chats
          </span>
        ) : null}
      </div>

      {!collapsed ? (
        <div className="border-b border-neutral-200/80 p-2">
          <button
            type="button"
            onClick={onNewChat}
            className="flex w-full items-center gap-2 rounded-lg border border-neutral-200/90 bg-neutral-50 px-3 py-2 text-left text-sm font-medium text-neutral-800 transition-colors hover:bg-neutral-100"
          >
            <Plus className="h-4 w-4 shrink-0 text-neutral-600" strokeWidth={2} />
            New chat
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-1 border-b border-neutral-200/80 py-2">
          <button
            type="button"
            onClick={onNewChat}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
            title="New chat"
            aria-label="New chat"
          >
            <Plus className="h-5 w-5" strokeWidth={2} />
          </button>
        </div>
      )}

      <nav className="min-h-0 flex-1 overflow-y-auto p-2" style={{ scrollbarWidth: "thin" }}>
        {isLoading ? (
          <ul className="space-y-1">
            {[1, 2, 3, 4].map((i) => (
              <li
                key={i}
                className="h-10 animate-pulse rounded-lg bg-neutral-100"
              />
            ))}
          </ul>
        ) : threads.length === 0 ? (
          !collapsed ? (
            <p className="px-2 py-4 text-center text-xs leading-relaxed text-neutral-400">
              No chats yet. Send a message below to start.
            </p>
          ) : (
            <div className="flex justify-center pt-2 text-neutral-300">
              <MessageSquare className="h-5 w-5" strokeWidth={1.5} />
            </div>
          )
        ) : (
          <ul className="space-y-0.5">
            {threads.map((t) => {
              const active = t.id === selectedThreadId;
              const label = formatThreadLabel(t.created_at);
              return (
                <li key={t.id} className="group flex items-stretch gap-0.5">
                  <button
                    type="button"
                    onClick={() => onSelectThread(t.id)}
                    title={label}
                    className={cn(
                      "flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors",
                      active
                        ? "bg-neutral-200/80 text-neutral-900"
                        : "text-neutral-700 hover:bg-neutral-100",
                      collapsed && "justify-center px-0",
                    )}
                  >
                    <MessageSquare
                      className={cn(
                        "h-4 w-4 shrink-0",
                        active ? "text-neutral-800" : "text-neutral-400",
                      )}
                      strokeWidth={1.75}
                    />
                    {!collapsed ? (
                      <span className="min-w-0 flex-1 truncate">{label}</span>
                    ) : null}
                  </button>
                  {!collapsed ? (
                    <button
                      type="button"
                      aria-label={`Delete chat: ${label}`}
                      className="flex shrink-0 items-center justify-center rounded-lg px-1.5 text-neutral-400 opacity-80 transition-colors hover:bg-red-50 hover:text-red-600 hover:opacity-100 focus:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onRequestDelete(t);
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" strokeWidth={1.75} />
                    </button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </nav>
    </aside>
  );
}

function formatThreadLabel(createdAt: string): string {
  const d = new Date(createdAt);
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  const time = d.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
  if (sameDay) return `Chat · ${time}`;
  return `Chat · ${d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  })}`;
}
