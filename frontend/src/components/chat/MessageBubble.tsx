"use client";

import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import "katex/dist/katex.min.css";
import type { MessageResponse } from "@/lib/api";

interface MessageBubbleProps {
  message: MessageResponse;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[85%] rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm"
          style={{ background: "#6366f1", color: "white", fontFamily: "var(--serif, 'Newsreader', Georgia, serif)", lineHeight: 1.55 }}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div
        className="max-w-[92%] rounded-2xl rounded-tl-sm px-4 py-3"
        style={{ background: "#ffffff", border: "1px solid #e5e2db" }}
      >
        <div className="chat-message-content" style={{ color: "#1a1a1a", fontSize: 13, lineHeight: 1.65 }}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
            components={{
              p: ({ children }) => (
                <p style={{ marginBottom: 10, color: "#1a1a1a", fontSize: 13 }}>{children}</p>
              ),
              code: ({ className, children }) => {
                const isBlock = !!className;
                if (isBlock) {
                  return (
                    <pre style={{ background: "#f3f4f6", borderRadius: 6, padding: "10px 14px", overflowX: "auto", margin: "8px 0" }}>
                      <code style={{ fontFamily: "var(--mono)", fontSize: 12, color: "#4338ca" }}>{children}</code>
                    </pre>
                  );
                }
                return (
                  <code style={{ fontFamily: "var(--mono)", fontSize: 12, color: "#4338ca", background: "#eef2ff", padding: "1px 5px", borderRadius: 4 }}>
                    {children}
                  </code>
                );
              },
              strong: ({ children }) => (
                <strong style={{ color: "#111827", fontWeight: 500 }}>{children}</strong>
              ),
              ul: ({ children }) => (
                <ul style={{ marginLeft: 20, marginBottom: 8 }}>{children}</ul>
              ),
              ol: ({ children }) => (
                <ol style={{ marginLeft: 20, marginBottom: 8 }}>{children}</ol>
              ),
              li: ({ children }) => (
                <li style={{ marginBottom: 4, fontSize: 13, color: "#1a1a1a" }}>{children}</li>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        {message.token_count != null && (
          <p style={{ fontFamily: "var(--mono)", fontSize: 10, color: "#9ca3af", marginTop: 6 }}>
            {message.token_count} tokens
          </p>
        )}
      </div>
    </div>
  );
}
