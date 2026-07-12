"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { ReportMeta } from "@/lib/api";

interface DeleteReportDialogProps {
  report: ReportMeta | null;
  open: boolean;
  loading: boolean;
  errorMessage?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

/**
 * Purpose: Confirm destructive delete for a report before calling the API.
 * Inputs: report metadata for display, open flag, loading, callbacks.
 * Outputs: Renders a modal with Cancel / Delete actions.
 */
export function DeleteReportDialog({
  report,
  open,
  loading,
  errorMessage,
  onCancel,
  onConfirm,
}: DeleteReportDialogProps) {
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

  const title = report?.title || report?.query || "this report";

  return (
    <AnimatePresence>
      {open && report && (
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
            aria-labelledby="delete-report-title"
            aria-describedby="delete-report-desc"
            className="w-full max-w-md rounded-2xl border p-6 shadow-xl"
            style={{
              background: "#fafaf8",
              borderColor: "var(--shell-border, #e5e2db)",
              boxShadow: "0 25px 50px -12px rgba(0,0,0,0.18)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2
              id="delete-report-title"
              className="text-xl font-medium text-[#141210]"
              style={{ fontFamily: "var(--serif, 'Newsreader', Georgia, serif)" }}
            >
              Delete report?
            </h2>
            <p
              id="delete-report-desc"
              className="mt-3 text-[15px] leading-relaxed text-[#5c5952]"
              style={{ fontFamily: "var(--serif, 'Newsreader', Georgia, serif)" }}
            >
              This will permanently remove{" "}
              <span className="font-medium text-[#2a2824]">&ldquo;{title}&rdquo;</span> and all
              its versions. This cannot be undone.
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
                {loading ? "Deleting…" : "Delete report"}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
