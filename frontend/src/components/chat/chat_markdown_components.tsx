"use client";

import type { Components } from "react-markdown";

/**
 * Shared ReactMarkdown component overrides for assistant chat bubbles.
 * GFM tables need a scroll wrapper and explicit cell padding (global base reset zeros th/td).
 */
export const chatAssistantMarkdownComponents: Partial<Components> = {
  table: ({ children }) => (
    <div className="chat-table-wrap">
      <table>{children}</table>
    </div>
  ),
};
