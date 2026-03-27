"""
ReportManagerAgent — proposes a hierarchical section tree for the report.

Three managers run in parallel, each assigned a distinct structural perspective
so their proposals are genuinely diverse and useful for the Lead to synthesise:

  Manager 1 — concept-first:       foundations → theory → math → applications
  Manager 2 — problem-first:       worked examples → required math → theory → generalisation
  Manager 3 — practitioner-workflow: when/why → implementation → edge cases → validation

The Report Lead then synthesises the best elements from all three.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from .report_tree import ReportTree, _extract_json, _enforce_node_count
from .section_node import SectionNode

if TYPE_CHECKING:
    from trace import TraceLogger


_PERSPECTIVES: dict[int, tuple[str, str]] = {
    1: (
        "concept-first",
        "Organise from foundational theory outward: start with definitions and axioms, "
        "build through mathematical formalism, then move to properties, proofs, and "
        "finally real-world applications. A reader should understand the 'why' deeply "
        "before encountering any worked examples.",
    ),
    2: (
        "problem-first",
        "Organise around concrete problems: open with a motivating worked example, "
        "then introduce only the mathematical machinery that example requires, then "
        "generalise to the full theory, then present further problems that expose "
        "each new layer. A reader learns by doing before they learn by reading.",
    ),
    3: (
        "practitioner-workflow",
        "Organise as a practitioner's guide: when and why to use this technique, "
        "step-by-step implementation with decision points, common edge cases and "
        "failure modes, validation strategies, and performance / complexity "
        "considerations. Theory appears only where it directly informs a decision.",
    ),
}


class ReportManagerAgent:
    """
    Calls the LLM once to produce a hierarchical section tree proposal.
    Each instance is assigned a distinct structural perspective via `_PERSPECTIVES`,
    ensuring the three parallel proposals are genuinely diverse.
    Three instances run in parallel via asyncio.gather in pipeline._phase_b.
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
        available_skills: list[str],
        audience: str = "practitioner",
        logger: "TraceLogger | None" = None,
    ) -> ReportTree:
        """
        Generate one tree proposal using this manager's assigned perspective.

        Args:
            query:            Research question driving the report.
            target_n:         Pre-rolled section count the tree must hit exactly.
            available_skills: Full set of tier-1 retrieval skills that will run
                              after planning (so the manager knows what evidence
                              types will be available when workers write).
            audience:         Target reader type (layperson / practitioner / expert …).
            logger:           Optional TraceLogger; when provided, logs prompt +
                              raw response + parsed tree for this manager call.

        Returns:
            ReportTree with exactly target_n nodes and proposal_id set.
        """
        perspective_name, perspective_desc = _PERSPECTIVES.get(
            self.manager_id, _PERSPECTIVES[1]
        )
        user_message = (
            f"query: {query}\n"
            f"strength_context: target_section_count={target_n}\n"
            f"available_retrieval_skills: {', '.join(available_skills)}\n"
            f"audience: {audience}\n"
            f"proposal_id: manager_{self.manager_id}\n"
            f"structural_perspective: {perspective_name}\n"
            f"perspective_instruction: {perspective_desc}\n\n"
            f"Produce exactly {target_n} nodes. Count before emitting."
        )

        raw = await asyncio.to_thread(
            self.client.generate_text,
            prompt=user_message,
            system_prompt=self._system_prompt,
            temperature=0.7,
        )

        tree = self._parse(raw, target_n)

        if logger is not None:
            logger.log_manager(
                manager_id=self.manager_id,
                system_prompt=self._system_prompt,
                user_message=user_message,
                raw_response=raw,
                parsed_tree_dict=tree.to_dict(),
            )

        return tree

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
