from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


def format_runtime_seconds(seconds: int) -> str:
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes}m {remainder}s" if remainder else f"{minutes}m"


@dataclass(frozen=True)
class RunCaps:
    """Hard limits carried in graph state and enforced at every transition."""

    qa_cycles: int
    max_nodes: int
    max_runtime_seconds: int
    llm_step_timeout_seconds: int = 300
    max_qa_suggestions_per_section: int = 2
    # Per-node tool-call budget. Deeper tiers get a larger budget so a node can
    # route to a domain tool AND still fetch several sources. Bounded to keep a
    # single node from monopolising the run.
    max_tool_calls_per_node: int = 4
    max_dag_depth: int = 4
    max_parallel_research_calls: int = 6

    # Content budgets — how much evidence reaches the LLM and how long its
    # output may run. These scale with strength so Quick mode stays cheap while
    # Deep mode gets proportionally richer context and a longer report. They are
    # product budgets rather than safety ceilings; see for_strength.
    max_evidence_per_node: int = 3
    max_source_chars: int = 12_000
    max_fetches: int = 2
    answer_completion_tokens: int = 1_200
    section_completion_tokens: int = 2_000
    subsection_completion_tokens: int = 1_500

    # Hard ceilings shared by every tier. Depth knobs scale with strength but
    # never exceed these, so no tier can schedule an unbounded run.
    MAX_TOOL_CALLS_CEILING: ClassVar[int] = 8
    MAX_FETCHES_CEILING: ClassVar[int] = 6

    def __post_init__(self) -> None:
        if self.qa_cycles < 0 or self.max_nodes < 1 or self.max_runtime_seconds < 1:
            raise ValueError("run caps must be positive, except qa_cycles")
        if self.max_qa_suggestions_per_section != 2:
            raise ValueError("QA suggestion cap is fixed at exactly 2 per section")
        if not 1 <= self.max_tool_calls_per_node <= self.MAX_TOOL_CALLS_CEILING:
            raise ValueError(
                f"per-node tool-call budget must be between 1 and {self.MAX_TOOL_CALLS_CEILING}"
            )
        if self.max_evidence_per_node < 1:
            raise ValueError("each node must surface at least one evidence record")
        if self.max_source_chars < 1_000:
            raise ValueError("per-source content budget is unreasonably small")
        if not 0 <= self.max_fetches <= self.MAX_FETCHES_CEILING:
            raise ValueError(
                f"resolver fetch cap must be between 0 and {self.MAX_FETCHES_CEILING}"
            )
        # A node must be able to fetch within its tool-call budget after spending
        # at least one call on discovery/search.
        if self.max_fetches > self.max_tool_calls_per_node - 1:
            raise ValueError("fetch cap must leave room for at least one search call")

    @classmethod
    def for_strength(cls, strength: int) -> "RunCaps":
        values = {
            # These are product budgets, not merely safety ceilings. Quick
            # research stays focused and cheap; Deep grows on every depth axis.
            # A reasoning model may legitimately spend several minutes on a
            # structured planning or writing completion.  The per-step limit
            # prevents one hung request from consuming the entire run, while
            # the outer deadline leaves room for planning, retrieval, QA, and
            # writing to finish in sequence.
            #
            # Content budgets climb with strength so a Deep report reasons over
            # more source text, routes to more tools per node, fetches more
            # pages, and writes longer sections and subsections.
            #                cycles nodes runtime     llm_step    tool_calls fetch ev  src_chars  ans_tok sec_tok sub_tok
            1: (0, 6, 20 * 60, 6 * 60,            4, 2,  6, 30_000, 3_000, 5_000, 1_500),
            2: (1, 10, 30 * 60, 7 * 60 + 30,      5, 3,  8, 45_000, 3_500, 7_000, 2_200),
            3: (2, 16, 60 * 60, 10 * 60,          6, 4, 10, 70_000, 4_000, 9_000, 3_000),
        }
        try:
            (
                cycles, nodes, runtime, llm_step_timeout,
                tool_calls, fetches, evidence, source_chars,
                answer_tokens, section_tokens, subsection_tokens,
            ) = values[strength]
        except KeyError as exc:
            raise ValueError("strength must be 1, 2, or 3") from exc
        return cls(
            cycles, nodes, runtime, llm_step_timeout,
            max_tool_calls_per_node=tool_calls,
            max_evidence_per_node=evidence,
            max_source_chars=source_chars,
            max_fetches=fetches,
            answer_completion_tokens=answer_tokens,
            section_completion_tokens=section_tokens,
            subsection_completion_tokens=subsection_tokens,
        )

    @classmethod
    def for_test(cls) -> "RunCaps":
        """Minimal single-node profile for real-inference smoke testing.

        One node, no QA cycles, and a single web_fetch, so a run makes exactly
        one search and one fetch (with search variants also capped to 1 by the
        resolver in test mode). Token budgets stay small to keep the real
        provider spend low. The fixed per-node tool-call and QA-suggestion caps
        are unchanged — this only shrinks the run, it does not relax invariants.
        """
        return cls(
            qa_cycles=0,
            max_nodes=1,
            max_runtime_seconds=10 * 60,
            llm_step_timeout_seconds=6 * 60,
            max_tool_calls_per_node=4,
            max_evidence_per_node=3,
            max_source_chars=12_000,
            max_fetches=1,
            answer_completion_tokens=1_200,
            section_completion_tokens=2_000,
            subsection_completion_tokens=1_500,
        )
