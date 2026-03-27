"""
Converts a Markdown research report string into a self-contained HTML file.

The Markdown is embedded as a JS literal; client-side Marked.js + KaTeX
auto-render handle the full rendering pipeline — no Python-side HTML generation.
Design system: editorial light, monospace accents (Newsreader + JetBrains Mono).
CDN stack: KaTeX 0.16.9 · Marked 9.1.6 · Chart.js 4.4.1.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from string import Template


_CSS = """\
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,300;0,400;0,500;1,300;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg:        #f7f5f0;
  --bg2:       #ffffff;
  --bg3:       #ece9e2;
  --border:    rgba(0,0,0,0.08);
  --border-hi: rgba(0,0,0,0.14);
  --text:      #2a2824;
  --text-dim:  #5c5952;
  --text-hi:   #141210;
  --accent:    #1a6fd4;
  --accent2:   #0d8a5b;
  --accent3:   #c45c00;
  --danger:    #c42d2d;
  --mono:      'JetBrains Mono', monospace;
  --serif:     'Newsreader', Georgia, serif;
  --radius:    8px;
  --radius-lg: 14px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html {
  scroll-behavior: smooth;
  color-scheme: light;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--serif);
  font-size: 17px;
  line-height: 1.75;
  min-height: 100vh;
}

/* ── Layout ── */
.page-outer {
  display: grid;
  grid-template-columns: 1fr;
  max-width: 860px;
  margin: 0 auto;
  padding: 48px 24px 96px;
}

@media (min-width: 1200px) {
  .page-outer {
    grid-template-columns: 220px 1fr;
    max-width: 1120px;
    gap: 56px;
    align-items: start;
  }
}

.page { min-width: 0; }

/* ── Header ── */
.report-header {
  border-bottom: 0.5px solid var(--border-hi);
  padding-bottom: 32px;
  margin-bottom: 48px;
}

.report-eyebrow {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  color: var(--accent);
  text-transform: uppercase;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.report-eyebrow::after {
  content: '';
  flex: 1;
  height: 0.5px;
  background: var(--border-hi);
}

.report-title {
  font-size: 28px;
  font-weight: 300;
  color: var(--text-hi);
  line-height: 1.3;
  margin-bottom: 14px;
  font-style: italic;
}

.report-meta {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--text-dim);
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

/* ── Markdown content ── */
.report-content { margin-bottom: 64px; }

.report-content h1 {
  font-size: 26px;
  font-weight: 300;
  color: var(--text-hi);
  font-style: italic;
  margin: 48px 0 16px;
  line-height: 1.3;
}

.report-content h2 {
  font-size: 20px;
  font-weight: 400;
  color: var(--text-hi);
  margin: 40px 0 12px;
  padding-bottom: 6px;
  border-bottom: 0.5px solid var(--border);
  font-family: var(--mono);
  letter-spacing: 0.02em;
}

.report-content h3 {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-hi);
  margin: 28px 0 10px;
  font-family: var(--mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.report-content h4 {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-dim);
  margin: 20px 0 8px;
  font-family: var(--mono);
}

.report-content h5,
.report-content h6 {
  font-size: 13px;
  color: var(--text-dim);
  margin: 16px 0 6px;
  font-family: var(--mono);
}

.report-content p {
  font-size: 16px;
  line-height: 1.85;
  margin-bottom: 18px;
  color: var(--text);
}

.report-content strong { color: var(--text-hi); font-weight: 500; }
.report-content em { font-style: italic; }

.report-content ul,
.report-content ol {
  margin: 0 0 18px 28px;
}

.report-content li {
  font-size: 16px;
  line-height: 1.8;
  color: var(--text);
  margin-bottom: 4px;
}

.report-content li > ul,
.report-content li > ol {
  margin-top: 4px;
  margin-bottom: 4px;
}

.report-content blockquote {
  border-left: 2px solid var(--accent);
  padding: 12px 18px;
  background: rgba(26,111,212,0.06);
  border-radius: 0 var(--radius) var(--radius) 0;
  margin: 20px 0;
}

.report-content blockquote p {
  font-size: 14px;
  color: var(--text-dim);
  margin-bottom: 0;
  line-height: 1.65;
}

.report-content hr {
  border: none;
  border-top: 0.5px solid var(--border);
  margin: 36px 0;
}

.report-content a {
  color: var(--accent);
  text-decoration: none;
}

.report-content a:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

/* ── Code blocks ── */
.report-content pre {
  background: var(--bg3);
  border: 0.5px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 22px;
  overflow-x: auto;
  margin: 16px 0 20px;
}

.report-content code {
  font-family: var(--mono);
  font-size: 13px;
  color: #1a5c40;
  line-height: 1.7;
}

.report-content p code,
.report-content li code {
  background: var(--bg3);
  border: 0.5px solid var(--border);
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 12px;
  color: var(--accent);
}

/* ── Tables ── */
.report-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
  font-size: 14px;
}

.report-content th {
  background: var(--bg3);
  border: 0.5px solid var(--border-hi);
  padding: 10px 14px;
  text-align: left;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-dim);
}

.report-content td {
  border: 0.5px solid var(--border);
  padding: 10px 14px;
  vertical-align: top;
  line-height: 1.6;
}

.report-content tr:hover td { background: rgba(0,0,0,0.03); }

/* ── Mobile math scroll ── */
.katex-display {
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  padding: 4px 0;
}

.report-content .katex { color: var(--text-hi); }

/* ── Footer ── */
.report-footer {
  border-top: 0.5px solid var(--border);
  padding-top: 24px;
  margin-top: 64px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--text-dim);
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

/* ── TOC Sidebar ── */
#toc {
  display: none;
}

@media (min-width: 1200px) {
  #toc {
    display: block;
    position: sticky;
    top: 32px;
    align-self: start;
    max-height: calc(100vh - 64px);
    overflow-y: auto;
    padding-right: 8px;
  }
}

.toc-label {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 10px;
}

.toc-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.toc-list li { margin: 0; }

.toc-list a {
  display: block;
  font-family: var(--mono);
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-dim);
  text-decoration: none;
  padding: 3px 0 3px 8px;
  border-left: 1.5px solid var(--border);
  transition: color 0.15s, border-color 0.15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.toc-list a:hover,
.toc-list a.toc-active {
  color: var(--accent);
  border-left-color: var(--accent);
}

.toc-list .toc-h3 a {
  padding-left: 18px;
  font-size: 10.5px;
}

/* ── Reference Section ── */
.ref-section {
  border-top: 0.5px solid var(--border-hi);
  margin-top: 48px;
  padding-top: 32px;
}

.ref-section h2 {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 20px;
  border-bottom: none !important;
  padding-bottom: 0 !important;
}

.ref-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ref-entry {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 12px;
  font-size: 13px;
  line-height: 1.55;
  padding: 10px 14px;
  background: var(--bg2);
  border: 0.5px solid var(--border);
  border-radius: var(--radius);
  scroll-margin-top: 80px;
}

.ref-key {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--accent);
  word-break: break-word;
  padding-top: 1px;
}

.ref-body { color: var(--text); }
.ref-body a { color: var(--accent); text-decoration: none; }
.ref-body a:hover { text-decoration: underline; }

.ref-meta {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-dim);
  margin-top: 2px;
}

/* ── Inline citation links ── */
.cite-link {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--accent2);
  text-decoration: none;
  border-bottom: 0.5px dashed var(--accent2);
  padding-bottom: 1px;
}

.cite-link:hover { color: var(--accent); border-bottom-color: var(--accent); }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 3px; }

@media (max-width: 600px) {
  .report-title { font-size: 22px; }
  .page-outer { padding: 32px 16px 64px; }
  .ref-entry { grid-template-columns: 1fr; gap: 4px; }
}
"""


_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light">
<title>$title</title>

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>

<style>
$css
</style>
</head>
<body>
<div class="page-outer">

  <nav id="toc" aria-label="Table of contents">
    <div class="toc-label">Contents</div>
    <ul class="toc-list" id="tocList"></ul>
  </nav>

  <div class="page">

    <header class="report-header">
      <div class="report-eyebrow">Research Report</div>
      <h1 class="report-title">$query_text</h1>
      <div class="report-meta">$meta_row</div>
    </header>

    <main id="reportContent" class="report-content"></main>

    <footer class="report-footer">
      <span>singularity / research-agent</span>
      <span>KaTeX 0.16.9 · Marked 9.1.6 · Chart.js 4.4.1</span>
      <span>$timestamp</span>
    </footer>

  </div>

</div>

<script>
(function () {

  // ── Helpers ────────────────────────────────────────────────────────────────

  function slugify(text) {
    return text.toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .trim();
  }

  // ── Step 1: Render Markdown + KaTeX ────────────────────────────────────────

  function renderMarkdownWithMath(markdown, targetEl) {
    // breaks:true — single \n → <br> for step-by-step derivations and math blocks.
    // gfm:true   — GitHub Flavored Markdown: tables, task lists, strikethrough.
    targetEl.innerHTML = marked.parse(markdown, { breaks: true, gfm: true });

    // KaTeX auto-render.  Python string.Template collapses:
    //   $$$$ → $$  (display math delimiter)
    //   $$   → $   (inline math delimiter)
    // Listing display before inline prevents $$ being consumed as two inlines.
    renderMathInElement(targetEl, {
      delimiters: [
        { left: '$$$$', right: '$$$$', display: true  },
        { left: '$$',   right: '$$',   display: false }
      ],
      throwOnError: false,
      trust: true
    });
  }

  // ── Step 2: Split content section from reference section ───────────────────

  function splitRefSection(contentEl) {
    // Find the "Reference List" h2 heading injected by the pipeline assembler.
    const headings = contentEl.querySelectorAll('h2');
    let refHeading = null;
    for (const h of headings) {
      if (/^reference/i.test(h.textContent.trim())) {
        refHeading = h;
        break;
      }
    }
    if (!refHeading) return;

    // Collect all sibling elements from that heading to the end of content.
    const refNodes = [];
    let node = refHeading;
    while (node) {
      const next = node.nextSibling;
      refNodes.push(node);
      node = next;
    }

    // Build the styled reference section outside the main content area.
    const refSection = document.createElement('section');
    refSection.className = 'ref-section';

    const refTitle = document.createElement('h2');
    refTitle.textContent = 'Reference List';
    refSection.appendChild(refTitle);

    // Build structured ref-entry cards from the <ul> bullet list.
    const refList = document.createElement('ul');
    refList.className = 'ref-list';

    for (const n of refNodes) {
      if (n.tagName === 'UL' || n.tagName === 'OL') {
        for (const li of n.querySelectorAll('li')) {
          // Each li starts with **[CiteKey]** — extract key and rest.
          const rawHtml = li.innerHTML;
          const keyMatch = rawHtml.match(/^<strong>\[([^\]]+)\]<\/strong>\s*/);
          if (!keyMatch) {
            // Not a structured entry — append as-is
            const plainLi = document.createElement('li');
            plainLi.innerHTML = rawHtml;
            refList.appendChild(plainLi);
            continue;
          }
          const key = keyMatch[1];
          const bodyHtml = rawHtml.slice(keyMatch[0].length);

          const entry = document.createElement('li');
          entry.className = 'ref-entry';
          entry.id = 'ref-' + key;

          const keyEl = document.createElement('div');
          keyEl.className = 'ref-key';
          keyEl.textContent = '[' + key + ']';

          const bodyEl = document.createElement('div');
          bodyEl.className = 'ref-body';

          // Separate the meta part (italic suffix after main link)
          const metaMatch = bodyHtml.match(/^([\s\S]*?)(\s*·\s*<em>.*<\/em>)?$/);
          if (metaMatch) {
            const mainHtml = metaMatch[1].trim();
            const metaHtml = metaMatch[2] ? metaMatch[2].replace(/^[\s·]+/, '') : '';
            bodyEl.innerHTML = mainHtml;
            if (metaHtml) {
              const metaEl = document.createElement('div');
              metaEl.className = 'ref-meta';
              metaEl.innerHTML = metaHtml;
              bodyEl.appendChild(metaEl);
            }
          } else {
            bodyEl.innerHTML = bodyHtml;
          }

          entry.appendChild(keyEl);
          entry.appendChild(bodyEl);
          refList.appendChild(entry);
        }
      } else if (n !== refHeading && n.nodeType === Node.ELEMENT_NODE) {
        // Any other element (hr, p, etc.) in the ref block — skip decorative ones
        if (n.tagName !== 'HR') refSection.appendChild(n.cloneNode(true));
      }
    }

    refSection.appendChild(refList);

    // Remove original ref nodes from content area and append styled section after.
    for (const n of refNodes) n.parentNode && n.parentNode.removeChild(n);
    contentEl.parentNode.insertBefore(refSection, contentEl.nextSibling);
  }

  // ── Step 3: Add anchor IDs to all headings ─────────────────────────────────

  function addHeadingAnchors(contentEl) {
    const slugCount = {};
    contentEl.querySelectorAll('h2, h3, h4').forEach(h => {
      const base = slugify(h.textContent);
      slugCount[base] = (slugCount[base] || 0) + 1;
      h.id = slugCount[base] > 1 ? base + '-' + slugCount[base] : base;
      h.style.scrollMarginTop = '24px';
    });
  }

  // ── Step 4: Build TOC from headings ────────────────────────────────────────

  function buildToc(contentEl) {
    const tocList = document.getElementById('tocList');
    if (!tocList) return;

    const headings = contentEl.querySelectorAll('h2, h3');
    if (headings.length < 3) return;  // too short to need a TOC

    headings.forEach(h => {
      const isH3 = h.tagName === 'H3';
      // Skip the reference section heading in TOC
      if (/^reference/i.test(h.textContent.trim())) return;

      const li = document.createElement('li');
      li.className = isH3 ? 'toc-h3' : 'toc-h2';

      const a = document.createElement('a');
      a.href = '#' + h.id;
      a.textContent = h.textContent;
      a.title = h.textContent;

      li.appendChild(a);
      tocList.appendChild(li);
    });

    // Highlight active section on scroll via IntersectionObserver
    const links = tocList.querySelectorAll('a');
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          links.forEach(l => l.classList.remove('toc-active'));
          const active = tocList.querySelector('a[href="#' + entry.target.id + '"]');
          if (active) active.classList.add('toc-active');
        }
      });
    }, { rootMargin: '-20% 0px -70% 0px' });

    contentEl.querySelectorAll('h2, h3').forEach(h => observer.observe(h));
  }

  // ── Step 5: Make inline [CiteKey] text nodes into anchor links ─────────────

  function linkCiteKeys(contentEl) {
    // Walk all text nodes inside the main content; skip ref-section.
    const walker = document.createTreeWalker(
      contentEl,
      NodeFilter.SHOW_TEXT,
      null
    );

    const CITE_RE = /\[([A-Za-z][A-Za-z0-9]{1,30})\]/g;
    const toReplace = [];

    let textNode;
    while ((textNode = walker.nextNode())) {
      // Don't touch nodes inside the reference section itself
      if (textNode.parentElement.closest('.ref-section')) continue;
      // Don't touch nodes inside <a> tags
      if (textNode.parentElement.closest('a')) continue;
      if (CITE_RE.test(textNode.textContent)) {
        toReplace.push(textNode);
      }
      CITE_RE.lastIndex = 0;
    }

    toReplace.forEach(tn => {
      const frag = document.createDocumentFragment();
      let lastIdx = 0;
      CITE_RE.lastIndex = 0;
      let m;
      while ((m = CITE_RE.exec(tn.textContent)) !== null) {
        if (m.index > lastIdx) {
          frag.appendChild(document.createTextNode(tn.textContent.slice(lastIdx, m.index)));
        }
        const refId = 'ref-' + m[1];
        const target = document.getElementById(refId);
        if (target) {
          const a = document.createElement('a');
          a.href = '#' + refId;
          a.className = 'cite-link';
          a.textContent = m[0];
          a.title = target.querySelector('.ref-body')?.textContent?.trim() || m[0];
          frag.appendChild(a);
        } else {
          frag.appendChild(document.createTextNode(m[0]));
        }
        lastIdx = m.index + m[0].length;
      }
      if (lastIdx < tn.textContent.length) {
        frag.appendChild(document.createTextNode(tn.textContent.slice(lastIdx)));
      }
      tn.parentNode.replaceChild(frag, tn);
    });
  }

  // ── Main ───────────────────────────────────────────────────────────────────

  const reportMarkdown = $markdown_json;
  const contentEl = document.getElementById('reportContent');

  renderMarkdownWithMath(reportMarkdown, contentEl);
  addHeadingAnchors(contentEl);
  splitRefSection(contentEl);
  buildToc(contentEl);
  linkCiteKeys(contentEl);

}());
</script>
</body>
</html>
""")


def _strip_report_boilerplate(markdown: str) -> str:
    """
    Removes the standard '# Research Report\\n\\n**Query:** ...\\n\\n---\\n' prefix
    that _format_report prepends, since the HTML page header handles that chrome.
    """
    return re.sub(
        r"^# Research Report\n\n\*\*Query:\*\*[^\n]*\n\n---\n\n?",
        "",
        markdown,
        count=1,
    )


def _escape_html(text: str) -> str:
    """Escapes characters that are unsafe inside an HTML attribute or text node."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class ReportHtmlRenderer:
    """
    Converts the Markdown string returned by run_pipeline (or _legacy_run) into a
    self-contained HTML file.

    The Markdown is embedded as a JSON-encoded JS literal; Marked.js parses it
    client-side and KaTeX auto-render processes all $...$ and $$...$$ expressions.
    The rendered HTML is cached by content hash so repeated renders are free.

    Usage:
        renderer = ReportHtmlRenderer()
        html = renderer.render(report_md, query="...", metadata={...})
        Path("final_report.html").write_text(html, encoding="utf-8")
    """

    def render(
        self,
        markdown: str,
        query: str,
        metadata: dict | None = None,
    ) -> str:
        """
        Produces a complete standalone HTML document.

        Args:
            markdown: Raw Markdown string from the pipeline.
            query:    Original research query (shown in the page header).
            metadata: Optional dict — recognised keys: strength (int), audience (str),
                      sections (int), words (int), generated_at (str).

        Returns:
            Full HTML string ready to write to a .html file.
        """
        meta = metadata or {}
        timestamp = meta.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M"))

        meta_parts: list[str] = []
        if "strength" in meta:
            meta_parts.append(f"Strength {meta['strength']}/10")
        if "audience" in meta:
            meta_parts.append(str(meta["audience"]))
        if "sections" in meta:
            meta_parts.append(f"{meta['sections']} sections")
        if "words" in meta:
            meta_parts.append(f"{meta['words']:,} words")
        meta_parts.append(timestamp)

        meta_row = " <span>·</span> ".join(
            f"<span>{p}</span>" for p in meta_parts
        )

        content_md = _strip_report_boilerplate(markdown)
        word_count = len(content_md.split())
        if "words" not in meta:
            meta_row += f" <span>·</span> <span>{word_count:,} words</span>"

        title = f"Research Report — {query[:72]}"

        return _TEMPLATE.substitute(
            title=_escape_html(title),
            query_text=_escape_html(query),
            meta_row=meta_row,
            markdown_json=json.dumps(content_md),
            css=_CSS,
            timestamp=_escape_html(timestamp),
        )
