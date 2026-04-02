"use client";

import { useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2 } from "lucide-react";
import { ApiError } from "@/lib/api";

interface PatchModalProps {
  open: boolean;
  selectedText: string;
  onClose: () => void;
  onSubmit: (instruction: string) => Promise<void>;
}

export function PatchModal({ open, selectedText, onClose, onSubmit }: PatchModalProps) {
  const [instruction, setInstruction] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleClose = useCallback(() => {
    if (loading) return;
    setInstruction("");
    setError(null);
    onClose();
  }, [loading, onClose]);

  const handleSubmit = useCallback(async () => {
    if (!instruction.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      await onSubmit(instruction.trim());
      setInstruction("");
      // parent closes modal on success
    } catch (e: any) {
      if (e instanceof ApiError) {
        if (e.status === 409) {
          setError("Document changed, reload to see the latest version before editing.");
        } else if (e.status === 422) {
          const detail = e.body?.detail;
          if (Array.isArray(detail)) {
            setError(detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join("; "));
          } else {
            setError(typeof detail === "string" ? detail : "Validation error — check your input.");
          }
        } else {
          setError(e.message || "Patch failed. Please try again.");
        }
      } else {
        setError(e?.message || "Patch failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }, [instruction, loading, onSubmit]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
            onClick={handleClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ duration: 0.18 }}
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-[var(--rpt-bg2)] border border-[var(--rpt-border-hi)] shadow-2xl overflow-hidden"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--rpt-border)]">
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--rpt-text-dim)" }}>
                Edit Selection
              </span>
              <button onClick={handleClose} className="text-[var(--rpt-text-dim)] hover:text-[var(--rpt-text-hi)] transition-colors">
                <X size={16} />
              </button>
            </div>

            <div className="px-5 py-4">
              {/* Selected text preview */}
              <div className="mb-4 rounded-lg bg-[var(--rpt-bg3)] border border-[var(--rpt-border)] px-4 py-3">
                <p style={{ fontFamily: "var(--mono)", fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--rpt-text-dim)", marginBottom: 6 }}>
                  Selected text
                </p>
                <p style={{ fontSize: 13, color: "var(--rpt-text)", lineHeight: 1.6, maxHeight: 80, overflow: "hidden", fontFamily: "var(--serif)" }}>
                  {selectedText.length > 200 ? selectedText.slice(0, 200) + "…" : selectedText}
                </p>
              </div>

              {/* Instruction input */}
              <label style={{ fontFamily: "var(--mono)", fontSize: 10, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--rpt-text-dim)", display: "block", marginBottom: 8 }}>
                Instruction
              </label>
              <textarea
                ref={textareaRef}
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit(); }}
                placeholder="e.g. Make this more concise, add a formula, simplify the language..."
                rows={3}
                className="w-full rounded-lg px-3 py-2.5 text-sm outline-none resize-none"
                style={{
                  background: "var(--rpt-bg)",
                  border: "0.5px solid var(--rpt-border-hi)",
                  color: "var(--rpt-text)",
                  fontFamily: "var(--serif)",
                  fontSize: 14,
                  lineHeight: 1.6,
                }}
                autoFocus
              />
              {error && (
                <p
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 12,
                    color: "var(--rpt-accent3)",
                    marginTop: 10,
                    padding: "8px 12px",
                    background: "rgba(196,92,0,0.07)",
                    border: "0.5px solid rgba(196,92,0,0.2)",
                    borderRadius: 6,
                  }}
                >
                  {error}
                </p>
              )}
            </div>

            <div className="flex items-center justify-between px-5 py-3 border-t border-[var(--rpt-border)]">
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--rpt-text-dim)" }}>⌘↵ to submit</span>
              <div className="flex gap-2">
                <button
                  onClick={handleClose}
                  className="px-4 py-2 rounded-lg text-sm transition-colors"
                  style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--rpt-text-dim)", background: "var(--rpt-bg3)" }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!instruction.trim() || loading}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm text-white transition-colors disabled:opacity-40"
                  style={{ fontFamily: "var(--mono)", fontSize: 12, background: "var(--rpt-accent)" }}
                >
                  {loading && <Loader2 size={12} className="animate-spin" />}
                  Apply Edit
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
