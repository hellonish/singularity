"""
ReportLeadAgent — receives three Manager proposals, selects/merges the best,
and emits the single authoritative final ReportTree.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

from agents.report_manager.report_tree import ReportTree, _enforce_node_count, _extract_json

if TYPE_CHECKING:
    from trace import TraceLogger

_SYSTEM_PROMPT = (Path(__file__).parent / "prompt.md").read_text(encoding="utf-8")


class ReportLeadAgent:
    def __init__(self, client):
        self.client = client
        self._system_prompt = _SYSTEM_PROMPT

    async def finalise(
        self,
        proposals: list[ReportTree],
        query: str,
        section_count_range: tuple[int, int],
        audience: str = "practitioner",
        logger: "TraceLogger | None" = None,
    ) -> ReportTree:
        """
        Takes 3 Manager proposals, returns the final authoritative tree.

        Args:
            proposals:            Three ReportTree proposals from the Managers.
            query:                Original research question.
            section_count_range:  (lo, hi) — final tree must stay within this range.
            audience:             Target reader type.
            logger:               Optional TraceLogger; logs the full Lead call when
                                  provided (proposals JSON, raw response, final tree).
        """
        lo, hi = section_count_range
        proposals_json = json.dumps(
            [p.to_dict() for p in proposals], indent=2
        )
        user_message = (
            f"query: {query}\n"
            f"audience: {audience}\n"
            f"target_section_count_range: {lo}–{hi} (stay within this range)\n\n"
            f"## Manager Proposals\n\n{proposals_json}"
        )

        raw = await asyncio.to_thread(
            self.client.generate_text,
            prompt=user_message,
            system_prompt=self._system_prompt,
            temperature=0.2,   # deterministic selection
        )

        tree = self._parse(raw, section_count_range)

        if logger is not None:
            logger.log_lead(
                system_prompt=self._system_prompt,
                user_message=user_message,
                raw_response=raw,
                final_tree_dict=tree.to_dict(),
            )

        return tree

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _parse(
        self, raw: str, section_count_range: tuple[int, int]
    ) -> ReportTree:
        data = _extract_json(raw)

        # Lead wraps its tree in a "final_tree" key
        inner = data.get("final_tree", data)
        tree = ReportTree.from_dict(inner)
        tree.proposal_id = "lead_final"

        lo, hi = section_count_range
        actual = len(tree.nodes)
        if not (lo <= actual <= hi):
            # Enforce to midpoint of range
            target = (lo + hi) // 2
            tree = _enforce_node_count(tree, target)

        return tree
