"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

interface StreamingMessageProps {
  content: string;
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="flex justify-start">
      <div
        className="max-w-[92%] rounded-2xl rounded-tl-sm px-4 py-3"
        style={{ background: "#ffffff", border: "1px solid #e5e2db" }}
      >
        <div style={{ color: "#1a1a1a", fontSize: 13, lineHeight: 1.65 }}>
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
            }}
          >
            {content}
          </ReactMarkdown>
          {/* Blinking cursor */}
          <span
            style={{
              display: "inline-block",
              width: 2,
              height: 14,
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
