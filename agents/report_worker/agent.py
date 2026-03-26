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
            analysis, chunks_text, children_content, audience
        )
        raw2 = await asyncio.to_thread(
            self.client.generate_text,
            prompt=call2_msg,
            system_prompt=self._system_prompt,
            temperature=0.3,
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
        children = self.tree.children_of(self.node.node_id)
        if not children:
            return ""
        parts = []
        for child in children:
            if child.content:
                parts.append(
                    f"### {child.title} (node {child.node_id})\n\n{child.content}"
                )
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
    def _format_chunks(chunks: list[Any]) -> tuple[str, dict[str, dict]]:
        """
        Format Qdrant chunks for the LLM and build a citation source map.

        Each chunk header embeds a pre-assigned citation key so the LLM uses
        it verbatim instead of inventing its own.

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
            cred  = getattr(chunk, "credibility", 0.0)
            title = getattr(chunk, "source_title", "Unknown")
            url   = getattr(chunk, "source_url", "")
            text  = getattr(chunk, "text", str(chunk))
            cite_id = ReportWorkerAgent._make_citation_id(title, used_keys)
            if cite_id not in source_map:
                source_map[cite_id] = {"title": title, "url": url}
            parts.append(
                f"[Chunk {i} | Cite as: {cite_id}] "
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
            msg += f"## Retrieved Evidence Chunks\n\n{chunks_text}\n\n"
        if children_content:
            msg += f"## Children Content (already written)\n\n{children_content}\n\n"
        return msg

    def _build_call2_message(
        self,
        analysis: dict[str, Any],
        chunks_text: str,
        children_content: str,
        audience: str,
    ) -> str:
        return (
            f"call: 2\n"
            f"section_node_id: {self.node.node_id}\n"
            f"section_title: {self.node.title}\n"
            f"audience: {audience}\n\n"
            f"## Analysis Results (from Call 1)\n\n"
            f"{json.dumps(analysis.get('analyses', {}), indent=2)}\n\n"
            f"## Citations Identified\n\n"
            f"{', '.join(analysis.get('citations_found', []) or [])}\n\n"
            + (f"## Children Content\n\n{children_content}\n\n" if children_content else "")
        )

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_call(raw: str, expected_call: int) -> dict[str, Any]:
        m = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
        text = m.group(1) if m else raw.strip()
        if not text.startswith("{"):
            # Find first {
            start = text.find("{")
            if start == -1:
                return {"call": expected_call, "content": raw, "analyses": {}}
            text = text[start:]
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text)
            return obj
        except (json.JSONDecodeError, ValueError):
            return {"call": expected_call, "content": raw, "analyses": {}}
