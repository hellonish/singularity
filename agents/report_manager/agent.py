"""
ReportManagerAgent — proposes a hierarchical section tree for the report.

Three managers run in parallel, each producing an independent proposal.
The Report Lead then selects / merges the best one.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from .report_tree import ReportTree, _extract_json, _enforce_node_count
from .section_node import SectionNode


class ReportManagerAgent:
    """
    Calls the LLM once to produce a hierarchical section tree proposal.
    Three instances run in parallel via asyncio.gather.
    """

    def __init__(self, manager_id: int, client):
        self.manager_id = manager_id
        self.client = client
        self._system_prompt = (Path(__file__).parent / "prompt.md").read_text(
            encoding="utf-8"
        )

    async def propose(
        self,
        query: str,
        target_n: int,
        active_skills: list[str],
        audience: str = "practitioner",
    ) -> ReportTree:
        """Generate one tree proposal. `target_n` is the pre-rolled section count."""
        user_message = (
            f"query: {query}\n"
            f"strength_context: target_section_count={target_n}\n"
            f"active_retrieval_skills: {', '.join(active_skills)}\n"
            f"audience: {audience}\n"
            f"proposal_id: manager_{self.manager_id}\n\n"
            f"Produce exactly {target_n} nodes. Count before emitting."
        )

        raw = await asyncio.to_thread(
            self.client.generate_text,
            prompt=user_message,
            system_prompt=self._system_prompt,
            temperature=0.7,   # diversity across 3 managers is desirable
        )

        return self._parse(raw, target_n)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _parse(self, raw: str, target_n: int) -> ReportTree:
        data = _extract_json(raw)
        tree = ReportTree.from_dict(data)

        actual = len(tree.nodes)
        if actual != target_n:
            # LLM missed the count — trim or duplicate to enforce constraint
            tree = _enforce_node_count(tree, target_n)

        tree.proposal_id = f"manager_{self.manager_id}"
        return tree
