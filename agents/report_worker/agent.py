"""
ReportWorkerAgent — writes one section of the report using 2 LLM calls.

Call 1: Multi-Analysis  — selects 3 tier2 skills, runs all in one structured pass
Call 2: Section Write   — uses Call 1 output to write the final Markdown section

Leaf workers analyse raw Qdrant evidence.
Parent workers synthesise their children's already-written content.
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
        chunks_text = self._format_chunks(qdrant_chunks)

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
    def _format_chunks(chunks: list[Any]) -> str:
        if not chunks:
            return "(no chunks retrieved)"
        parts = []
        for i, chunk in enumerate(chunks):
            cred = getattr(chunk, "credibility", 0.0)
            title = getattr(chunk, "source_title", "Unknown")
            url = getattr(chunk, "source_url", "")
            text = getattr(chunk, "text", str(chunk))
            parts.append(
                f"[Chunk {i}] Source: {title} ({url}) | credibility={cred:.2f}\n{text}"
            )
        return "\n\n".join(parts)

    def _build_call1_message(
        self,
        chunks_text: str,
        children_content: str,
        audience: str,
        research_query: str,
    ) -> str:
        msg = (
            f"call: 1\n"
            f"section_node_id: {self.node.node_id}\n"
            f"section_title: {self.node.title}\n"
            f"section_description: {self.node.description}\n"
            f"section_type: {self.node.section_type}\n"
            f"node_level: {self.node.level} / max_depth: {self.tree.max_depth}\n"
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
