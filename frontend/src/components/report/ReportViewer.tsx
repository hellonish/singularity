"use client";

import "@/styles/report-content.css";
import "katex/dist/katex.min.css";

import React, { useCallback, useEffect, useMemo, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { normalizeMathMarkdown } from "@/lib/normalize_math_markdown";
import { truncateDisplayLabel } from "@/lib/utils";

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

// Custom heading components that add IDs for TOC anchors (dedupe slug collisions)
function makeHeading(
  level: 1 | 2 | 3 | 4 | 5 | 6,
  slugCounts: Map<string, number>,
) {
  return function Heading({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
    const text = React.Children.toArray(children)
      .map((c) => (typeof c === "string" ? c : ""))
      .join("");
    const base = slugify(text);
    const n = (slugCounts.get(base) ?? 0) + 1;
    slugCounts.set(base, n);
    const id = n === 1 ? base : `${base}-${n}`;
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

const CITE_KEY_RE = /\[([A-Za-z][A-Za-z0-9]{1,30})\]/g;

/** Readable short label for an http(s) URL (hostname + path, truncated). */
function citationUrlLabel(href: string, maxLen = 44): string {
  try {
    const u = new URL(href);
    const host = u.hostname.replace(/^www\./, "");
    const path = u.pathname + u.search + u.hash;
    const compact = path && path !== "/" ? `${host}${path}` : host;
    return truncateDisplayLabel(compact, maxLen);
  } catch {
    return truncateDisplayLabel(href.replace(/^https?:\/\//, ""), maxLen);
  }
}

function isInsideReferenceListSection(textNode: Node, root: HTMLElement): boolean {
  const ul = textNode.parentElement?.closest("ul");
  if (!ul || !root.contains(ul)) return false;
  let prev: Element | null = ul.previousElementSibling;
  while (prev) {
    if (
      prev.tagName === "H2" &&
      /^reference list$/i.test(prev.textContent?.trim() ?? "")
    ) {
      return true;
    }
    prev = prev.previousElementSibling;
  }
  return false;
}

type CiteRefMeta = { href: string; title: string };

/** Map citation keys (without brackets) → URL + list title (markdown link text) from Reference List. */
function buildCiteKeyMetaMap(root: HTMLElement): Map<string, CiteRefMeta> {
  const map = new Map<string, CiteRefMeta>();
  root.querySelectorAll("h2").forEach((h2) => {
    if (!/^reference list$/i.test(h2.textContent?.trim() ?? "")) return;
    let sib: Element | null = h2.nextElementSibling;
    while (sib && sib.tagName !== "UL") sib = sib.nextElementSibling;
    if (!sib || sib.tagName !== "UL") return;
    sib.querySelectorAll(":scope > li").forEach((li) => {
      const strong = li.querySelector("strong");
      const raw = strong?.textContent?.trim() ?? "";
      const m = raw.match(/^\[([A-Za-z][A-Za-z0-9]{1,30})\]$/);
      const link = li.querySelector('a[href^="http"]') as HTMLAnchorElement | null;
      if (m?.[1] && link?.href) {
        const titleRaw = (link.textContent || "").trim();
        const title =
          titleRaw.length > 0 ? titleRaw : citationUrlLabel(link.href);
        map.set(m[1], { href: link.href, title });
        if (!li.id) li.id = `ref-${m[1]}`;
      }
    });
  });
  return map;
}

/**
 * Renders markdown in isolation so parent re-renders (TOC state, session polling, etc.)
 * do not pass new `components` into ReactMarkdown. Imperative citation patches replace
 * DOM nodes; reconciling with a new components map caused insertBefore NotFoundError.
 */
const ReportMarkdownBody = React.memo(function ReportMarkdownBody({ source }: { source: string }) {
  const components = useMemo(() => {
    const slugCounts = new Map<string, number>();
    return {
      h1: makeHeading(1, slugCounts),
      h2: makeHeading(2, slugCounts),
      h3: makeHeading(3, slugCounts),
      h4: makeHeading(4, slugCounts),
      h5: makeHeading(5, slugCounts),
      h6: makeHeading(6, slugCounts),
      code({ className, children, ...props }: React.HTMLAttributes<HTMLElement> & { inline?: boolean }) {
        const isInline = !className;
        if (isInline) return <code {...props}>{children}</code>;
        return (
          <pre>
            <code className={className} {...props}>{children}</code>
          </pre>
        );
      },
      table({ children, ...props }: React.HTMLAttributes<HTMLTableElement>) {
        return (
          <div style={{ overflowX: "auto" }}>
            <table {...props}>{children}</table>
          </div>
        );
      },
    };
  }, [source]);

  return (
    <ReactMarkdown
      key={source}
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={components as any}
    >
      {source}
    </ReactMarkdown>
  );
});

interface ReportViewerProps {
  content: string;
  onTOCReady?: (entries: TOCEntry[]) => void;
  onSelection?: (text: string, headingSlug: string | null) => void;
}

export function ReportViewer({ content, onTOCReady, onSelection }: ReportViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const markdownSource = normalizeMathMarkdown(content);

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
  }, [markdownSource, onTOCReady]);

  // Post-render: turn [CiteKey] into links — prefer external URL from Reference List.
  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;
    const citeMetaMap = buildCiteKeyMetaMap(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const toReplace: Text[] = [];
    let node: Text | null;
    while ((node = walker.nextNode() as Text | null)) {
      if (node.parentElement?.closest("a, .ref-section, code, pre")) continue;
      if (isInsideReferenceListSection(node, root)) continue;
      CITE_KEY_RE.lastIndex = 0;
      if (CITE_KEY_RE.test(node.textContent || "")) toReplace.push(node);
      CITE_KEY_RE.lastIndex = 0;
    }
    toReplace.forEach((tn) => {
      const frag = document.createDocumentFragment();
      let last = 0;
      CITE_KEY_RE.lastIndex = 0;
      let m: RegExpExecArray | null;
      const text = tn.textContent || "";
      while ((m = CITE_KEY_RE.exec(text)) !== null) {
        if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        const key = m[1];
        const meta = citeMetaMap.get(key);
        if (meta) {
          const a = document.createElement("a");
          a.href = meta.href;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          a.className = "cite-link cite-link--external";
          const titleShown = truncateDisplayLabel(meta.title, 200);
          a.textContent = `${m[0]} ${titleShown}`.trim();
          a.title = `${meta.title}\n${meta.href}`;
          frag.appendChild(a);
        } else {
          const target = document.getElementById(`ref-${key}`);
          if (target) {
            const a = document.createElement("a");
            a.href = `#ref-${key}`;
            a.className = "cite-link";
            a.textContent = m[0];
            a.title =
              (target.querySelector(".ref-body") as HTMLElement)?.innerText?.trim() ||
              m[0];
            frag.appendChild(a);
          } else {
            frag.appendChild(document.createTextNode(m[0]));
          }
        }
        last = m.index + m[0].length;
      }
      if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
      tn.parentNode?.replaceChild(frag, tn);
    });
  }, [markdownSource]);

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

  return (
    <div
      ref={containerRef}
      className="report-content"
      onMouseUp={handleMouseUp}
    >
      <ReportMarkdownBody source={markdownSource} />
    </div>
  );
}
