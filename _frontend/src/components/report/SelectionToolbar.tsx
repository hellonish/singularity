"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Pencil, Copy } from "lucide-react";

interface SelectionToolbarProps {
  selectedText: string;
  onEdit: () => void;
}

export function SelectionToolbar({ selectedText, onEdit }: SelectionToolbarProps) {
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);

  useEffect(() => {
    if (!selectedText) { setPosition(null); return; }
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) { setPosition(null); return; }
    try {
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      setPosition({
        top: rect.top + window.scrollY - 48,
        left: rect.left + rect.width / 2,
      });
    } catch { setPosition(null); }
  }, [selectedText]);

  const handleCopy = () => {
    navigator.clipboard.writeText(selectedText).catch(() => {});
  };

  return (
    <AnimatePresence>
      {position && selectedText && (
        <motion.div
          initial={{ opacity: 0, y: 4, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 4, scale: 0.95 }}
          transition={{ duration: 0.12 }}
          style={{ position: "absolute", top: position.top, left: position.left, transform: "translateX(-50%)", zIndex: 100 }}
        >
          <div className="flex items-center gap-1 rounded-lg bg-white border border-[#e5e2db] shadow-xl px-2 py-1.5">
            <button
              onClick={onEdit}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium text-white bg-[#1a6fd4] hover:bg-[#1560c0] transition-colors"
              style={{ fontFamily: "var(--mono)" }}
            >
              <Pencil size={11} />
              Edit
            </button>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-[#6b7280] hover:text-[#1a1a1a] hover:bg-[#f3f4f6] transition-colors"
            >
              <Copy size={11} />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
