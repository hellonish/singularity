"""
StrengthConfig — single source of truth for all strength-derived quantities.

strength: int 1–10 controls retrieval breadth, section count, query fanout,
Qdrant chunk budget per worker, and Phase C+ augmentation budgets.
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
        """
        Number of unique retrieval skills to activate.
        Floor raised to 2 so every run has at minimum web_search + one domain skill.

        s:  1  2  3  4  5  6  7  8  9  10
        n:  2  3  5  7  9 10 12 14 16  18
        """
        return max(2, int(1.8 * self.value))

    @property
    def queries_per_skill(self) -> int:
        """
        Adaptive query fanout per skill.
        Floor raised to 4 so even strength=1 produces meaningful coverage.
        max(4, ceil(s/2)*2) — scales smoothly, plateaus at 10 for s≥9.

        s:  1  2  3  4  5  6  7  8  9  10
        Q:  4  4  4  4  6  6  8  8  10 10
        """
        return max(4, math.ceil(self.value / 2) * 2)

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
    # Worker Context Budget  (Issue 2 Fix 3: scaled with strength)
    # ------------------------------------------------------------------

    def qdrant_k(self, node_level: int, max_depth: int) -> int:
        """
        Number of Qdrant chunks for a worker.  Scales with strength so
        high-strength runs get proportionally richer evidence context.

        Base values by tier:
          leaf              → base 8  + strength  (s=1: 9,  s=10: 18)
          parent-of-leaf    → base 6  + strength  (s=1: 7,  s=10: 16)
          chapter/root      → base 4  + strength  (s=1: 5,  s=10: 14)

        Previously: leaf=15, parent-of-leaf=8, chapter=3 (flat, no strength scaling).
        """
        if node_level >= max_depth:
            return 8 + self.value        # leaf
        elif node_level >= max_depth - 1:
            return 6 + self.value        # parent of leaf (was fixed 8, now 7–16)
        else:
            return 4 + self.value        # chapter / root (was fixed 3, now 5–14)

    @property
    def min_chunks_per_leaf(self) -> int:
        """
        Minimum acceptable Qdrant chunks for a leaf section before the
        Layer 1 coverage audit flags it for a targeted follow-up retrieval.
        """
        return max(3, self.value)

    # ------------------------------------------------------------------
    # Phase C+ Augmentation Budgets  (Issue 3)
    # ------------------------------------------------------------------

    @property
    def max_augmentation_iters(self) -> int:
        """
        Maximum evidence augmentation loop iterations per leaf section.
        All strength levels now get at least 2 iterations (per spec).

        s:  1–7 → 2,  8–9 → 3,  10 → 4
        """
        if self.value <= 7:
            return 2
        elif self.value <= 9:
            return 3
        return 4

    @property
    def max_web_escalations(self) -> int:
        """
        Maximum web search escalations per leaf section within the
        augmentation loop.

        s:  1–7 → 1,  8–9 → 2,  10 → 3
        """
        if self.value <= 7:
            return 1
        elif self.value <= 9:
            return 2
        return 3

    @property
    def augmentation_entity_extraction(self) -> bool:
        """Pre-loop entity extraction enabled at all strength levels."""
        return True

    @property
    def augmentation_faithfulness_check(self) -> bool:
        """Post-Call2 faithfulness annotation enabled at all strength levels."""
        return True

    # ------------------------------------------------------------------
    # Issue 2 Fix 4: Section-normalized query budget
    # ------------------------------------------------------------------

    def effective_queries_per_skill(self, num_leaf_sections: int) -> int:
        """
        Ensures each leaf section gets at minimum 1 dedicated query.

        If the formula-based queries_per_skill × retrieval_skill_count
        would produce fewer total queries than the number of leaf sections,
        scale up queries_per_skill to compensate.

        Returns the effective queries_per_skill to use for this run.
        """
        formula_total = self.retrieval_skill_count * self.queries_per_skill
        min_total = max(num_leaf_sections, formula_total)
        if min_total == formula_total:
            return self.queries_per_skill
        return math.ceil(min_total / self.retrieval_skill_count)

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
        Expected total LLM calls per run (2-call worker model + augmentation):
        5 (planner + 3 managers + lead) + 2 × N_avg + aug_overhead
        """
        aug_overhead = self.max_augmentation_iters * self.expected_section_count // 2
        return 5 + 2 * self.expected_section_count + aug_overhead

    def __repr__(self) -> str:
        lo, hi = self.section_count_range
        return (
            f"StrengthConfig(s={self.value}, "
            f"skills={self.retrieval_skill_count}, "
            f"queries/skill={self.queries_per_skill}, "
            f"sections={lo}–{hi}, "
            f"aug_iters={self.max_augmentation_iters}, "
            f"web_esc={self.max_web_escalations})"
        )
