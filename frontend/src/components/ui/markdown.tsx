'use client';

import { memo, useState } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import 'katex/dist/katex.min.css';

// LLMs frequently emit math with LaTeX-style \( \) and \[ \] delimiters, but
// remark-math only recognizes dollar delimiters ($…$, $$…$$). Rewrite the LaTeX
// delimiters to dollar form so the math actually renders. This must run on the
// raw source (before markdown parsing) because remark treats "\(" as an escaped
// "(" and drops the backslash. Fenced and inline code spans are masked out first
// so their contents are never rewritten.
function normalizeMathDelimiters(src: string): string {
  const codeSpans: string[] = [];
  const placeholder = (i: number) => ` CODE${i} `;

  // Mask fenced code blocks (``` … ```) and inline code (`…`) so we don't touch
  // LaTeX-looking text inside them.
  const masked = src
    .replace(/```[\s\S]*?```/g, (m) => placeholder(codeSpans.push(m) - 1))
    .replace(/`[^`\n]*`/g, (m) => placeholder(codeSpans.push(m) - 1));

  const rewritten = masked
    // \[ … \] is display math: surround with blank lines so remark-math treats
    // it as a block ($$ on its own lines) rather than inline.
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, m) => `\n\n$$\n${m.trim()}\n$$\n\n`)
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, m) => `$${m}$`);

  // Restore the masked code spans.
  return rewritten.replace(/ CODE(\d+) /g, (_, i) => codeSpans[Number(i)]);
}

// A small globe drawn inline so the citation popover carries no external asset.
function GlobeIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" style={{ flexShrink: 0, opacity: 0.75 }} aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18" />
    </svg>
  );
}

type CiteLink = { url: string; title: string };

// The backend collapses every source that shares a host into one <cite> chip so
// the reader never sees "github.com" repeated. `data-links` packs the exact URLs
// (link fields joined by "|", links joined by "||") which we surface on hover.
function parseLinks(raw: string | undefined): CiteLink[] {
  if (!raw) return [];
  return raw
    .split('||')
    .map((entry) => {
      const [url, ...rest] = entry.split('|');
      return { url: url ?? '', title: rest.join('|') || url || '' };
    })
    .filter((link) => link.url);
}

function Citation({ host, links }: { host: string; links: CiteLink[] }) {
  const [open, setOpen] = useState(false);
  if (!links.length) return <span>{host}</span>;

  return (
    <span
      style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <a
        href={links[0].url}
        target="_blank"
        rel="noopener noreferrer"
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: '3px',
          padding: '0 6px', margin: '0 1px', height: '17px', lineHeight: '17px',
          fontSize: '11px', fontFamily: 'var(--font-mono)',
          color: 'var(--accent-2, var(--accent))', background: 'var(--accent-soft)',
          border: '1px solid var(--border)', borderRadius: '999px',
          textDecoration: 'none', verticalAlign: 'baseline', whiteSpace: 'nowrap',
        }}
      >
        {host}
        {links.length > 1 && <span style={{ opacity: 0.6 }}>·{links.length}</span>}
      </a>
      {open && (
        <span
          role="group"
          style={{
            position: 'absolute', top: 'calc(100% + 6px)', left: 0, zIndex: 40,
            minWidth: '220px', maxWidth: '340px',
            padding: '6px', display: 'flex', flexDirection: 'column', gap: '2px',
            border: '1px solid var(--border-strong, var(--border))', borderRadius: '10px',
            background: 'var(--surface)', boxShadow: 'var(--shadow)',
          }}
        >
          <span className="sg-mono" style={{ padding: '3px 7px 5px', fontSize: '9px', letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)' }}>{host}</span>
          {links.map((link) => (
            <a
              key={link.url}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'flex', alignItems: 'center', gap: '7px',
                padding: '6px 7px', borderRadius: '7px',
                fontSize: '11.5px', lineHeight: 1.35, color: 'var(--text)',
                textDecoration: 'none', wordBreak: 'break-word',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--accent-soft)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <GlobeIcon />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{link.title}</span>
            </a>
          ))}
        </span>
      )}
    </span>
  );
}

const components: Components = {
  table: ({ children }) => <div className="chat-table-wrap"><table>{children}</table></div>,
  a: ({ children, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer">{children}</a>,
  // Custom inline citation. Only the known data-* attributes are honored; any
  // other markup rehype-raw passes through is rendered as ordinary text/elements.
  cite: ({ node }) => {
    const props = (node?.properties ?? {}) as Record<string, unknown>;
    const host = typeof props.dataHost === 'string' ? props.dataHost : '';
    const links = parseLinks(typeof props.dataLinks === 'string' ? props.dataLinks : undefined);
    if (!host) return null;
    return <Citation host={host} links={links} />;
  },
};

export const Markdown = memo(function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeRaw, rehypeKatex]}
      components={components}
    >
      {normalizeMathDelimiters(children)}
    </ReactMarkdown>
  );
});
