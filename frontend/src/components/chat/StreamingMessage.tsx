"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

import { normalizeChatAssistantMarkdown } from "@/lib/normalize_chat_assistant_markdown";
import { chatAssistantMarkdownComponents } from "@/components/chat/chat_markdown_components";

interface StreamingMessageProps {
  content: string;
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="flex w-full min-w-0 justify-start">
      <div
        className="max-w-[92%] min-w-0 rounded-2xl rounded-tl-sm px-4 py-3"
        style={{ background: "#ffffff", border: "1px solid #e5e2db" }}
      >
        <div
          className="chat-message-content"
          style={{ color: "#1a1a1a", fontSize: 16, lineHeight: 1.65 }}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
            components={{
              ...chatAssistantMarkdownComponents,
              p: ({ children }) => (
                <p style={{ marginBottom: 10, color: "#1a1a1a", fontSize: 16 }}>{children}</p>
              ),
              code: ({ className, children }) => {
                const isBlock = !!className;
                if (isBlock) {
                  return (
                    <pre style={{ background: "#f3f4f6", borderRadius: 6, padding: "10px 14px", overflowX: "auto", margin: "8px 0" }}>
                      <code style={{ fontFamily: "var(--mono)", fontSize: 14, color: "#4338ca" }}>{children}</code>
                    </pre>
                  );
                }
                return (
                  <code style={{ fontFamily: "var(--mono)", fontSize: 13, color: "#4338ca", background: "#eef2ff", padding: "1px 5px", borderRadius: 4 }}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {normalizeChatAssistantMarkdown(content)}
          </ReactMarkdown>
          {/* Blinking cursor */}
          <span
            style={{
              display: "inline-block",
              width: 2,
              height: 17,
              background: "#6366f1",
              borderRadius: 1,
              marginLeft: 2,
              verticalAlign: "middle",
              animation: "blink 1s step-end infinite",
            }}
          />
        </div>
        <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
      </div>
    </div>
  );
}
