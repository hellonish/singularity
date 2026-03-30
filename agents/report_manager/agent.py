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

_SYSTEM_PROMPT = (Path(__file__).parent / "prompt.md").read_text(encoding="utf-8")

_PERSPECTIVES: dict[int, dict] = {
    1: {
        "name": "concept-first",
        "role": (
            "You are a foundational-theory architect. Your structure reveals WHY something "
            "works, not just what it does. You begin at axioms and build outward so a reader "
            "achieves deep conceptual understanding before encountering any applied examples."
        ),
        "instruction": (
            "Organise from foundational theory outward: start with definitions and axioms, "
            "build through mathematical formalism, then move to properties, proofs, and "
            "finally real-world applications. A reader should understand the 'why' deeply "
            "before encountering any worked examples."
        ),
        "key_questions": [
            "What is the minimal set of definitions needed to ground everything else?",
            "What first-principles make this technique inevitable rather than arbitrary?",
            "Where do the mathematical formalism and the intuition diverge — and why does that matter?",
        ],
        "anti_patterns": [
            "Do NOT open with a use case before establishing the conceptual foundation.",
            "Do NOT bury the formal definition inside an application section.",
            "Do NOT write a chapter titled 'Introduction' that is just background — make it a conceptual claim.",
        ],
    },
    2: {
        "name": "problem-first",
        "role": (
            "You are a pedagogy-first architect. Your structure leads with difficulty: the "
            "reader is immediately confronted with a real problem and acquires theory only as "
            "it becomes necessary to solve what they are already working on."
        ),
        "instruction": (
            "Organise around concrete problems: open with a motivating worked example, "
            "then introduce only the mathematical machinery that example requires, then "
            "generalise to the full theory, then present further problems that expose "
            "each new layer. A reader learns by doing before they learn by reading."
        ),
        "key_questions": [
            "What is the single most clarifying worked example — the one that makes everything click?",
            "What is the minimum theory needed to solve the first problem — and nothing more?",
            "What new problems appear as capability grows, forcing the theory to generalise?",
        ],
        "anti_patterns": [
            "Do NOT begin with definitions or axioms — begin with a problem the reader can feel.",
            "Do NOT introduce mathematical machinery before the need for it is concrete.",
            "Do NOT use 'in general' as a chapter opener — save generalisation for after worked problems.",
        ],
    },
    3: {
        "name": "practitioner-workflow",
        "role": (
            "You are a practitioner's guide architect. Your structure answers the questions "
            "a working engineer or analyst actually asks: when do I use this, how do I use "
            "it, what breaks, and how do I verify it worked."
        ),
        "instruction": (
            "Organise as a practitioner's guide: when and why to use this technique, "
            "step-by-step implementation with decision points, common edge cases and "
            "failure modes, validation strategies, and performance/complexity "
            "considerations. Theory appears only where it directly informs a decision."
        ),
        "key_questions": [
            "What decision gate tells a practitioner when to reach for this technique vs. an alternative?",
            "What are the top-3 failure modes, and how does the practitioner detect and recover from each?",
            "What does 'done correctly' look like — what can be measured, tested, or audited?",
        ],
        "anti_patterns": [
            "Do NOT lead with history or theory — lead with a decision ('When to use this').",
            "Do NOT write a section that is pure background with no actionable guidance.",
            "Do NOT treat validation as a footnote — it should be a first-class chapter.",
        ],
    },
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
        self._system_prompt = _SYSTEM_PROMPT

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
        p = _PERSPECTIVES.get(self.manager_id, _PERSPECTIVES[1])
        perspective_name = p["name"]
        perspective_instruction = (
            f"ROLE: {p['role']}\n\n"
            f"STRUCTURE PRINCIPLE: {p['instruction']}\n\n"
            f"KEY QUESTIONS — your tree must answer these:\n"
            + "\n".join(f"  - {q}" for q in p["key_questions"])
            + "\n\nANTI-PATTERNS — explicitly avoid:\n"
            + "\n".join(f"  ✗ {ap}" for ap in p["anti_patterns"])
        )
        user_message = (
            f"query: {query}\n"
            f"strength_context: target_section_count={target_n}\n"
            f"available_retrieval_skills: {', '.join(available_skills)}\n"
            f"audience: {audience}\n"
            f"proposal_id: manager_{self.manager_id}\n"
            f"structural_perspective: {perspective_name}\n"
            f"perspective_instruction:\n{perspective_instruction}\n\n"
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
