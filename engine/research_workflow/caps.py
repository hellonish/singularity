from __future__ import annotations

from dataclasses import dataclass


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

    def __post_init__(self) -> None:
        if self.qa_cycles < 0 or self.max_nodes < 1 or self.max_runtime_seconds < 1:
            raise ValueError("run caps must be positive, except qa_cycles")
        if self.max_qa_suggestions_per_section != 2:
            raise ValueError("QA suggestion cap is fixed at exactly 2 per section")
        if self.max_tool_calls_per_node != 4:
            raise ValueError("research node tool-call cap is fixed at exactly 4")
        if self.max_evidence_per_node < 1:
            raise ValueError("each node must surface at least one evidence record")
        if self.max_source_chars < 1_000:
            raise ValueError("per-source content budget is unreasonably small")
        if not 0 <= self.max_fetches <= 2:
            raise ValueError("resolver fetch cap must be between 0 and 2")

    @classmethod
    def for_strength(cls, strength: int) -> "RunCaps":
        values = {
            # These are product budgets, not merely safety ceilings. Quick
            # research is intended for a focused answer, so it has one node
            # and no LLM QA pass.
            # A reasoning model may legitimately spend several minutes on a
            # structured planning or writing completion.  The per-step limit
            # prevents one hung request from consuming the entire run, while
            # the outer deadline leaves room for planning, retrieval, QA, and
            # writing to finish in sequence.
            #
            # Content budgets (evidence, source_chars, fetches, answer_tokens,
            # section_tokens) climb with strength so a Deep report both reasons
            # over more source text and writes longer sections. The fetch cap
            # is hard-limited to 2 by the resolver regardless of tier.
            #                cycles nodes  runtime      llm_step   ev  src_chars fetch ans_tok sec_tok
            1: (0, 6, 20 * 60, 6 * 60,          6, 30_000, 2, 3_000, 5_000),
            2: (1, 8, 30 * 60, 7 * 60 + 30,     6, 40_000, 2, 3_500, 6_000),
            3: (2, 12, 60 * 60, 10 * 60,        8, 60_000, 2, 4_000, 7_500),
        }
        try:
            (
                cycles, nodes, runtime, llm_step_timeout,
                evidence, source_chars, fetches, answer_tokens, section_tokens,
            ) = values[strength]
        except KeyError as exc:
            raise ValueError("strength must be 1, 2, or 3") from exc
        return cls(
            cycles, nodes, runtime, llm_step_timeout,
            max_evidence_per_node=evidence,
            max_source_chars=source_chars,
            max_fetches=fetches,
            answer_completion_tokens=answer_tokens,
            section_completion_tokens=section_tokens,
        )
