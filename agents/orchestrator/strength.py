"""
StrengthConfig — single source of truth for all strength-derived quantities.

strength: int 1–10 controls retrieval breadth, section count, query fanout,
and Qdrant chunk budget per worker.
"""
import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class StrengthConfig:
    value: int  # 1–10

    def __post_init__(self) -> None:
        if not 1 <= self.value <= 10:
            raise ValueError(f"strength must be 1–10, got {self.value}")

    # ------------------------------------------------------------------
    # Retrieval Phase
    # ------------------------------------------------------------------

    @property
    def retrieval_skill_count(self) -> int:
        """Number of unique retrieval skills to activate: int(1.8 × s)."""
        return int(1.8 * self.value)

    @property
    def queries_per_skill(self) -> int:
        """
        Adaptive query fanout per skill.
        max(3, ceil(s/2)*2) — scales smoothly, plateaus at 10 for s≥9.

        s:  1  2  3  4  5  6  7  8  9  10
        Q:  3  3  4  4  6  6  8  8  10 10
        """
        return max(3, math.ceil(self.value / 2) * 2)

    @property
    def total_retrieval_calls(self) -> int:
        return self.retrieval_skill_count * self.queries_per_skill

    # ------------------------------------------------------------------
    # Report Structure
    # ------------------------------------------------------------------

    @property
    def section_count_range(self) -> tuple[int, int]:
        """Inclusive range [lo, hi] for total section-tree node count."""
        return (self.value * 6, self.value * 10)

    def sample_section_count(self) -> int:
        """
        Roll the section count for this run.
        Call ONCE at Manager time; store the result — never re-roll.
        """
        lo, hi = self.section_count_range
        return random.randint(lo, hi)

    # ------------------------------------------------------------------
    # Worker Context Budget
    # ------------------------------------------------------------------

    def qdrant_k(self, node_level: int, max_depth: int) -> int:
        """
        Number of Qdrant chunks to retrieve for a worker at `node_level`.
        Leaf nodes get maximum raw-source context; root/chapter nodes
        get minimal chunks (children already synthesised the evidence).

        node_level: 0 = root, max_depth = leaf
        """
        if node_level >= max_depth:
            return 15   # leaf — maximum evidence
        elif node_level >= max_depth - 1:
            return 8    # one level above leaf
        else:
            return 3    # chapter / root — children carry the evidence

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def expected_section_count(self) -> int:
        """Expected value of section count: s × 8."""
        return self.value * 8

    @property
    def expected_llm_calls(self) -> int:
        """
        Expected total LLM calls per run (2-call worker model):
        5 (planner + 3 managers + lead) + 2 × N_avg
        """
        return 5 + 2 * self.expected_section_count

    def __repr__(self) -> str:
        lo, hi = self.section_count_range
        return (
            f"StrengthConfig(s={self.value}, "
            f"skills={self.retrieval_skill_count}, "
            f"queries/skill={self.queries_per_skill}, "
            f"sections={lo}–{hi}, "
            f"llm_calls≈{self.expected_llm_calls})"
        )
