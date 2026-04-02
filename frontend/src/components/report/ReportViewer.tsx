"use client";

import "@/styles/report-content.css";
import "katex/dist/katex.min.css";

import React, { useCallback, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

// Slug function — must match backend patch/slug.py
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .trim()
    .replace(/^-+|-+$/g, "");
}

// Custom heading components that add IDs for TOC anchors
function makeHeading(level: 1 | 2 | 3 | 4 | 5 | 6) {
  return function Heading({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
    const text = React.Children.toArray(children)
      .map((c) => (typeof c === "string" ? c : ""))
      .join("");
    const id = slugify(text);
    const headingProps = { id, style: { scrollMarginTop: "80px" }, ...props };
    switch (level) {
      case 1: return <h1 {...headingProps}>{children}</h1>;
      case 2: return <h2 {...headingProps}>{children}</h2>;
      case 3: return <h3 {...headingProps}>{children}</h3>;
      case 4: return <h4 {...headingProps}>{children}</h4>;
      case 5: return <h5 {...headingProps}>{children}</h5>;
      case 6: return <h6 {...headingProps}>{children}</h6>;
    }
  };
}

export interface TOCEntry {
  id: string;
  text: string;
  level: 2 | 3;
}

interface ReportViewerProps {
  content: string;
  onTOCReady?: (entries: TOCEntry[]) => void;
  onSelection?: (text: string, headingSlug: string | null) => void;
}

export function ReportViewer({ content, onTOCReady, onSelection }: ReportViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Build TOC after render
  useEffect(() => {
    if (!containerRef.current || !onTOCReady) return;
    const entries: TOCEntry[] = [];
    containerRef.current.querySelectorAll("h2, h3").forEach((el) => {
      const level = parseInt(el.tagName[1]) as 2 | 3;
      const text = (el as HTMLElement).innerText;
      if (/^reference/i.test(text)) return; // skip ref section heading
      entries.push({ id: el.id, text, level });
    });
    onTOCReady(entries);
  }, [content, onTOCReady]);

  // Post-render: linkify [CiteKey] text nodes
  useEffect(() => {
    if (!containerRef.current) return;
    const CITE_RE = /\[([A-Za-z][A-Za-z0-9]{1,30})\]/g;
    const walker = document.createTreeWalker(
      containerRef.current,
      NodeFilter.SHOW_TEXT,
    );
    const toReplace: Text[] = [];
    let node: Text | null;
    while ((node = walker.nextNode() as Text | null)) {
      if (node.parentElement?.closest("a, .ref-section")) continue;
      if (CITE_RE.test(node.textContent || "")) toReplace.push(node);
      CITE_RE.lastIndex = 0;
    }
    toReplace.forEach((tn) => {
      const frag = document.createDocumentFragment();
      let last = 0;
      CITE_RE.lastIndex = 0;
      let m: RegExpExecArray | null;
      while ((m = CITE_RE.exec(tn.textContent || "")) !== null) {
        if (m.index > last) frag.appendChild(document.createTextNode((tn.textContent || "").slice(last, m.index)));
        const target = document.getElementById(`ref-${m[1]}`);
        if (target) {
          const a = document.createElement("a");
          a.href = `#ref-${m[1]}`;
          a.className = "cite-link";
          a.textContent = m[0];
          a.title = (target.querySelector(".ref-body") as HTMLElement)?.innerText?.trim() || m[0];
          frag.appendChild(a);
        } else {
          frag.appendChild(document.createTextNode(m[0]));
        }
        last = m.index + m[0].length;
      }
      if (last < (tn.textContent || "").length) frag.appendChild(document.createTextNode((tn.textContent || "").slice(last)));
      tn.parentNode?.replaceChild(frag, tn);
    });
  }, [content]);

  // Text selection → patch toolbar
  const handleMouseUp = useCallback(() => {
    if (!onSelection) return;
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) {
      onSelection("", null);
      return;
    }
    const selected = sel.toString().trim();
    // Find nearest preceding heading for slug
    const range = sel.getRangeAt(0);
    let node: Node | null = range.startContainer;
    let headingSlug: string | null = null;
    while (node && node !== containerRef.current) {
      let sib: Node | null = node.previousSibling || node.parentElement?.previousSibling || null;
      while (sib) {
        if ((sib as Element).tagName?.match(/^H[123456]$/)) {
          headingSlug = (sib as HTMLElement).id || null;
          sib = null;
          node = null;
          break;
        }
        sib = sib.previousSibling;
      }
      if (node) node = node.parentNode;
    }
    onSelection(selected, headingSlug);
  }, [onSelection]);

  const components = {
    h1: makeHeading(1),
    h2: makeHeading(2),
    h3: makeHeading(3),
    h4: makeHeading(4),
    h5: makeHeading(5),
    h6: makeHeading(6),
    // Code blocks
    code({ className, children, ...props }: React.HTMLAttributes<HTMLElement> & { inline?: boolean }) {
      const isInline = !className;
      if (isInline) return <code {...props}>{children}</code>;
      return (
        <pre>
          <code className={className} {...props}>{children}</code>
        </pre>
      );
    },
    // Tables — wrapped for horizontal scroll on mobile
    table({ children, ...props }: React.HTMLAttributes<HTMLTableElement>) {
      return (
        <div style={{ overflowX: "auto" }}>
          <table {...props}>{children}</table>
        </div>
      );
    },
  };

  return (
    <div
      ref={containerRef}
      className="report-content"
      onMouseUp={handleMouseUp}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components as any}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
