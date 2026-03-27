"""
ReportWorkerAgent — writes one section of the report using 2 LLM calls.

Call 1: Multi-Analysis  — selects 3 tier2 skills, runs all in one structured pass
Call 2: Section Write   — uses Call 1 output to write the final Markdown section

Leaf workers analyse raw Qdrant evidence.
Parent workers synthesise their children's already-written content.

Citation tracking: each chunk is pre-assigned a stable citation key derived from its
source title. The key is shown to the LLM in the chunk header ("Cite as: [Key]") so
the LLM uses it verbatim. The resulting citation_id → {title, url} mapping is stored
on the SectionNode and returned in WorkerResult, then aggregated into the Reference
List in the pipeline assembler.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

from agents.report_manager.section_node import SectionNode
from agents.report_manager.report_tree import ReportTree
from .result import WorkerResult


_STOP_WORDS = frozenset({
    "the", "a", "an", "of", "in", "on", "at", "for", "and", "or", "to", "by",
    "with", "from", "as", "is", "it", "its", "into", "this", "that", "are",
    "was", "were", "be", "been", "has", "have", "had", "do", "does", "did",
    "about", "using", "via", "based", "new", "some", "how", "why", "what",
})


class ReportWorkerAgent:
    """
    One instance per section node.  Instantiate, call run(), discard.
    """

    def __init__(self, node: SectionNode, tree: ReportTree, run_id: str, client):
        self.node    = node
        self.tree    = tree
        self.run_id  = run_id
        self.client  = client
        self._is_leaf = len(tree.children_of(node.node_id)) == 0

        prompt_file = (
            "prompt_leaf.md" if self._is_leaf
            else "prompt_parent.md"
        )
        self._system_prompt = (Path(__file__).parent / prompt_file).read_text(encoding="utf-8")

    async def run(
        self,
        qdrant_chunks: list[Any],     # list of DocumentChunk objects
        audience: str = "practitioner",
        research_query: str = "",
    ) -> WorkerResult:
        """Execute Call 1 (analysis) then Call 2 (write)."""
        children_content = self._gather_children_content()
        chunks_text, source_map = self._format_chunks(qdrant_chunks)

        # ── Call 1: Multi-Analysis ────────────────────────────────────
        call1_msg = self._build_call1_message(
            chunks_text, children_content, audience, research_query
        )
        raw1 = await asyncio.to_thread(
            self.client.generate_text,
            prompt=call1_msg,
            system_prompt=self._system_prompt,
            temperature=0.2,
        )
        analysis = self._parse_call(raw1, expected_call=1)

        # ── Call 2: Section Write ─────────────────────────────────────
        call2_msg = self._build_call2_message(
            analysis, chunks_text, children_content, audience,
            raw_chunks=qdrant_chunks,
        )
        raw2 = await asyncio.to_thread(
            self.client.generate_text,
            prompt=call2_msg,
            system_prompt=self._system_prompt,
            temperature=0.65,
        )
        write_out = self._parse_call(raw2, expected_call=2)

        # ── Persist content back onto the tree node ───────────────────
        content = write_out.get("content", "")
        citations = write_out.get("citations_used", [])
        self.node.content    = content
        self.node.word_count = write_out.get("word_count", len(content.split()))
        self.node.citations  = citations
        self.node.source_map = source_map

        return WorkerResult(
            node_id=self.node.node_id,
            section_title=self.node.title,
            content=content,
            word_count=self.node.word_count,
            node_type="leaf" if self._is_leaf else "parent",
            tier2_used=analysis.get("tier2_selected", []),
            tier3_used=write_out.get("tier3_selected", "report_generator"),
            citations_used=citations,
            qdrant_chunks_used=analysis.get("key_evidence_chunks", []),
            children_consumed=[c.node_id for c in self.tree.children_of(self.node.node_id)],
            coverage_gaps=write_out.get("coverage_gaps", []),
            source_map=source_map,
        )

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    def _gather_children_content(self) -> str:
        """
        Concatenates the already-written content of all direct children for
        the parent worker's context.  Node IDs are intentionally omitted —
        they are internal identifiers and must not appear in written prose.
        """
        children = self.tree.children_of(self.node.node_id)
        if not children:
            return ""
        parts = []
        for child in children:
            if child.content:
                parts.append(f"### {child.title}\n\n{child.content}")
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _make_citation_id(title: str, used_keys: set[str]) -> str:
        """
        Derive a stable, short PascalCase citation key from a source title.

        Skips stop words, joins up to 3 meaningful words (capped at 22 chars),
        and appends a numeric suffix on collision.
        Returns a bracketed key like `[ComplexityMatters]`.
        """
        clean = re.sub(r"[^\w\s]", " ", title)
        words = [w.capitalize() for w in clean.split() if w.lower() not in _STOP_WORDS and w.isalpha()]
        base = "".join(words[:3])[:22] if words else "Source"
        key, suffix = base, 2
        while key in used_keys:
            key = f"{base}{suffix}"
            suffix += 1
        used_keys.add(key)
        return f"[{key}]"

    @staticmethod
    def _resolve_title(title: str, url: str) -> str:
        """
        Returns a human-readable source label for citation purposes.

        If the stored title is empty, 'Unknown', a generic placeholder, or a
        tool-generated label like 'PDF chunk (pages X-Y)', derives a label
        from the URL domain to avoid polluting the Reference List with
        [Unknown] / [PdfChunkPages10] keys.
        """
        _GENERIC = {"unknown", "untitled", "source", ""}
        if title and title.lower() not in _GENERIC and not title.lower().startswith("pdf chunk"):
            return title
        if url:
            # Strip scheme and www, take first path segment as context
            import re as _re
            domain = _re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
            path_hint = url.rstrip("/").split("/")[-1][:30]
            if path_hint and not path_hint.startswith("http"):
                return f"{domain} — {path_hint}"
            return domain
        return "Source"

    @staticmethod
    def _format_chunks(chunks: list[Any]) -> tuple[str, dict[str, dict]]:
        """
        Format Qdrant chunks for the LLM and build a citation source map.

        Each chunk header embeds a pre-assigned citation key so the LLM uses
        it verbatim instead of inventing its own.  Titles are resolved via
        _resolve_title so generic 'Unknown' entries are replaced with domain
        labels before the citation key is generated.

        Returns:
            chunks_text: formatted string passed to the LLM prompt.
            source_map:  dict mapping citation_id → {title, url} for the
                         Reference List assembled by the pipeline.
        """
        if not chunks:
            return "(no chunks retrieved)", {}
        parts: list[str] = []
        source_map: dict[str, dict] = {}
        used_keys: set[str] = set()
        for i, chunk in enumerate(chunks):
            cred        = getattr(chunk, "credibility", 0.0)
            raw_title   = getattr(chunk, "source_title", "") or ""
            url         = getattr(chunk, "source_url", "") or ""
            source_type = getattr(chunk, "source_type", "") or ""
            date        = getattr(chunk, "date", "") or ""
            text        = getattr(chunk, "text", str(chunk))
            title = ReportWorkerAgent._resolve_title(raw_title, url)
            cite_id = ReportWorkerAgent._make_citation_id(title, used_keys)
            if cite_id not in source_map:
                source_map[cite_id] = {
                    "title":       title,
                    "url":         url,
                    "source_type": source_type,
                    "date":        date,
                }
            parts.append(
                f"[Evidence {i} | Cite as: {cite_id}] "
                f"Source: {title} ({url}) | credibility={cred:.2f}\n{text}"
            )
        return "\n\n".join(parts), source_map

    def _heading_marker(self) -> str:
        """Return the Markdown heading prefix (_walk uses depth+1, root starts at depth=1)."""
        root_level = self.tree.root.level
        walk_depth = (self.node.level - root_level) + 1
        return "#" * min(walk_depth + 1, 6)

    def _build_call1_message(
        self,
        chunks_text: str,
        children_content: str,
        audience: str,
        research_query: str,
    ) -> str:
        heading_marker = self._heading_marker()
        msg = (
            f"call: 1\n"
            f"section_node_id: {self.node.node_id}\n"
            f"section_title: {self.node.title}\n"
            f"section_description: {self.node.description}\n"
            f"section_type: {self.node.section_type}\n"
            f"node_level: {self.node.level} / max_depth: {self.tree.max_depth}\n"
            f"section_heading: {heading_marker} {self.node.title}  "
            f"(assembler adds this — do NOT include it in your content; use deeper levels for internal sub-headings)\n"
            f"audience: {audience}\n"
            f"research_query: {research_query}\n\n"
        )
        if chunks_text and chunks_text != "(no chunks retrieved)":
            msg += f"## Retrieved Evidence\n\n{chunks_text}\n\n"
        if children_content:
            msg += f"## Children Content (already written)\n\n{children_content}\n\n"
        return msg

    def _build_call2_message(
        self,
        analysis: dict[str, Any],
        chunks_text: str,
        children_content: str,
        audience: str,
        raw_chunks: list[Any] | None = None,
    ) -> str:
        """
        Builds the Call 2 (write) prompt.

        Passes analysis results from Call 1 plus the raw text of the top-3 key
        evidence chunks (as identified by `key_evidence_chunks` in Call 1 output)
        so the writer has direct access to specific quotes, statistics, and formulas
        instead of relying solely on the lossy analysis digest.
        """
        key_chunk_text = ""
        if raw_chunks:
            top_idxs = analysis.get("key_evidence_chunks", [])[:3]
            excerpts = []
            for idx in top_idxs:
                if isinstance(idx, int) and idx < len(raw_chunks):
                    chunk = raw_chunks[idx]
                    text = getattr(chunk, "text", "")[:600]
                    excerpts.append(f"[Evidence {idx}]\n{text}")
            if excerpts:
                key_chunk_text = (
                    "## Key Evidence Excerpts (direct text for quoting)\n\n"
                    + "\n\n".join(excerpts)
                    + "\n\n"
                )

        return (
            f"call: 2\n"
            f"section_node_id: {self.node.node_id}\n"
            f"section_title: {self.node.title}\n"
            f"audience: {audience}\n\n"
            f"## Analysis Results (from Call 1)\n\n"
            f"{json.dumps(analysis.get('analyses', {}), indent=2)}\n\n"
            f"## Citations Identified\n\n"
            f"{', '.join(analysis.get('citations_found', []) or [])}\n\n"
            + key_chunk_text
            + (f"## Children Content\n\n{children_content}\n\n" if children_content else "")
        )

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_json_newlines(text: str) -> str:
        """
        Escapes literal newline and carriage-return characters that appear
        inside JSON string values — turning them into the valid JSON escape
        sequences \\n and \\r respectively.

        LLMs occasionally emit multi-line JSON strings with real newlines
        instead of \\n, producing invalid JSON that json.loads rejects.  This
        character-by-character scan fixes that without touching escape
        sequences that are already correctly encoded.

        Only affects characters inside double-quoted string values; structural
        JSON whitespace (newlines between keys/values) is left untouched.
        """
        result: list[str] = []
        in_string = False
        escape_next = False
        for ch in text:
            if escape_next:
                result.append(ch)
                escape_next = False
            elif ch == "\\":
                result.append(ch)
                escape_next = True
            elif ch == '"':
                result.append(ch)
                in_string = not in_string
            elif in_string and ch == "\n":
                result.append("\\n")
            elif in_string and ch == "\r":
                result.append("\\r")
            else:
                result.append(ch)
        return "".join(result)

    @staticmethod
    def _parse_call(raw: str, expected_call: int) -> dict[str, Any]:
        """
        Parses a JSON response from the LLM.

        Tries three extraction strategies in order:
        1. JSON inside a ```json ... ``` code fence (sanitised first).
        2. Raw JSON object starting at the first `{` (sanitised first).
        3. Regex extraction of the `"content"` field from a JSON-shaped string —
           fallback for when the outer JSON is still malformed after sanitisation.
           Captured group is re-encoded before json.loads to handle any remaining
           literal newlines, preventing raw JSON blobs in the final report.
        """
        sanitize = ReportWorkerAgent._sanitize_json_newlines

        # Strategy 1: code-fenced JSON
        m = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
        text = sanitize(m.group(1) if m else raw.strip())

        # Strategy 2: bare JSON object
        if not text.startswith("{"):
            start = text.find("{")
            if start != -1:
                text = text[start:]

        if text.startswith("{"):
            try:
                decoder = json.JSONDecoder()
                obj, _ = decoder.raw_decode(text)
                return obj
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 3: regex extraction of "content" field from malformed JSON.
        # [^"\\] inside a character class matches literal newlines; re.DOTALL is
        # set as belt-and-suspenders but has no effect on character classes.
        content_match = re.search(
            r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, re.DOTALL
        )
        if content_match:
            try:
                # Replace any surviving literal newlines in the captured value
                # before wrapping in quotes and re-parsing as a JSON string.
                captured = (
                    content_match.group(1)
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                )
                content_str = json.loads(f'"{captured}"')
                citations_match = re.search(
                    r'"citations_used"\s*:\s*(\[[^\]]*\])', raw
                )
                citations = []
                if citations_match:
                    try:
                        citations = json.loads(citations_match.group(1))
                    except json.JSONDecodeError:
                        pass
                return {
                    "call": expected_call,
                    "content": content_str,
                    "citations_used": citations,
                    "analyses": {},
                }
            except (json.JSONDecodeError, ValueError):
                pass

        return {"call": expected_call, "content": raw, "analyses": {}}
