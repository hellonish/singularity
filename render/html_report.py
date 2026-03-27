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
.page {
  max-width: 860px;
  margin: 0 auto;
  padding: 48px 24px 96px;
}

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

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 3px; }

@media (max-width: 600px) {
  .report-title { font-size: 22px; }
  .page { padding: 32px 16px 64px; }
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

<script>
(function () {
  // Content hash cache — skips KaTeX re-render for unchanged sections
  const renderCache = new Map();

  function simpleHash(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) {
      h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
    }
    return h.toString(36);
  }

  function renderMarkdownWithMath(markdown, targetEl) {
    const hash = simpleHash(markdown);
    if (renderCache.has(hash)) {
      targetEl.innerHTML = renderCache.get(hash);
      return;
    }

    // breaks:true — single \n renders as <br> so step-by-step derivations,
    // worked examples, and multi-line math blocks stay on separate lines.
    // gfm:true — GitHub Flavored Markdown: tables, task lists, strikethrough.
    targetEl.innerHTML = marked.parse(markdown, { breaks: true, gfm: true });

    // KaTeX auto-render: $$ (display) must be listed before $ (inline) so the
    // engine does not consume the opening $$ of a display block as two inlines.
    // Python string.Template collapses $$$$ → $$ and $$ → $ in the output HTML.
    renderMathInElement(targetEl, {
      delimiters: [
        { left: '$$$$', right: '$$$$', display: true  },
        { left: '$$',   right: '$$',   display: false }
      ],
      throwOnError: false,
      trust: true
    });

    renderCache.set(hash, targetEl.innerHTML);
  }

  const reportMarkdown = $markdown_json;
  renderMarkdownWithMath(reportMarkdown, document.getElementById('reportContent'));
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
