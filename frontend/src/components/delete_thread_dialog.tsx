"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { ThreadSummaryResponse } from "@/lib/api";

interface DeleteThreadDialogProps {
  thread: ThreadSummaryResponse | null;
  open: boolean;
  loading: boolean;
  errorMessage?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

/**
 * Purpose: Confirm deletion of a chat thread before calling the API.
 * Inputs: thread row, open flag, loading, optional API error, callbacks.
 * Outputs: Modal with Cancel / Delete chat.
 */
export function DeleteThreadDialog({
  thread,
  open,
  loading,
  errorMessage,
  onCancel,
  onConfirm,
}: DeleteThreadDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  const label = thread
    ? new Date(thread.created_at).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "";

  return (
    <AnimatePresence>
      {open && thread && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          style={{ background: "rgba(0,0,0,0.45)" }}
          role="presentation"
          onClick={loading ? undefined : onCancel}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ type: "spring", damping: 26, stiffness: 320 }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-thread-title"
            aria-describedby="delete-thread-desc"
            className="w-full max-w-md rounded-2xl border p-6 shadow-xl"
            style={{
              background: "#fafaf8",
              borderColor: "var(--shell-border, #e5e2db)",
              boxShadow: "0 25px 50px -12px rgba(0,0,0,0.18)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2
              id="delete-thread-title"
              className="text-xl font-medium text-[#141210]"
              style={{ fontFamily: "var(--serif, 'Newsreader', Georgia, serif)" }}
            >
              Delete chat?
            </h2>
            <p
              id="delete-thread-desc"
              className="mt-3 text-[15px] leading-relaxed text-[#5c5952]"
              style={{ fontFamily: "var(--serif, 'Newsreader', Georgia, serif)" }}
            >
              This removes the conversation started{" "}
              <span className="font-medium text-[#2a2824]">{label}</span>. This cannot be
              undone.
            </p>
            {errorMessage ? (
              <p
                className="mt-3 text-sm text-red-600"
                style={{ fontFamily: "var(--mono, 'JetBrains Mono', monospace)", fontSize: 12 }}
                role="alert"
              >
                {errorMessage}
              </p>
            ) : null}
            <div className="mt-6 flex justify-end gap-3">
              <button
                ref={cancelRef}
                type="button"
                disabled={loading}
                onClick={onCancel}
                className="rounded-xl px-4 py-2.5 text-sm text-[#374151] transition-colors hover:bg-black/5 disabled:opacity-50"
                style={{ fontFamily: "var(--mono, 'JetBrains Mono', monospace)", fontSize: 12 }}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={onConfirm}
                className="rounded-xl px-4 py-2.5 text-sm font-medium text-white transition-opacity disabled:opacity-50"
                style={{
                  fontFamily: "var(--mono, 'JetBrains Mono', monospace)",
                  fontSize: 12,
                  background: "#c42d2d",
                }}
              >
                {loading ? "Deleting…" : "Delete chat"}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
