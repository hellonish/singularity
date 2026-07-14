"""Graph routing: QA gap suggestions must be researched before writing.

The cycle count gates QA *reviews*; every accepted suggestion — including
those from the final review — gets one resolution pass so the writer never
receives permanently unanswered nodes.
"""
import asyncio
import uuid
from typing import Any

from engine.research_workflow.caps import RunCaps
from engine.research_workflow.dag import ResearchDAG, ResearchNode, ResearchNodeStatus
from engine.research_workflow.workflow import ResearchWorkflow


class StubPlanner:
    async def polish_prompt(self, query: str) -> dict[str, Any]:
        return {"query": query, "audience": "practitioner", "constraints": []}

    async def parallel_proposals(self, query: str) -> list[dict[str, Any]]:
        return [{"perspective": "coverage", "nodes": []}]


class StubLead:
    async def merge(self, query: str, proposals, caps) -> ResearchDAG:
        dag = ResearchDAG()
        dag.add_node(ResearchNode(node_id="root", question=query, section_id="s1", level=0), caps)
        return dag


class SuggestingQA:
    """Adds one gap-filling suggestion on every review pass."""

    def __init__(self) -> None:
        self.review_calls = 0

    async def review(self, dag: ResearchDAG, caps) -> list[dict[str, Any]]:
        self.review_calls += 1
        parent = dag.nodes["root"]
        suggestion = ResearchNode(
            node_id=f"gap{self.review_calls}",
            question=f"Gap question {self.review_calls}",
            section_id="s1",
            level=1,
            depends_on=[parent.node_id],
        )
        accepted, rejected = dag.add_suggestions("s1", [suggestion], caps)
        return [{
            "section_id": "s1", "passed": False, "score": 0.5, "gaps": ["gap"],
            "accepted_suggestions": accepted, "rejected_suggestions": rejected,
        }]


class CapturingWriter:
    def __init__(self) -> None:
        self.dag: ResearchDAG | None = None

    async def write(self, dag: ResearchDAG, query: str, caps=None) -> dict[str, Any]:
        self.dag = dag
        return {
            "schema_version": "research-document-v1",
            "title": "T", "query": query, "sections": [], "references": [], "limitations": [],
        }


def _run(caps: RunCaps) -> tuple[list[str], SuggestingQA, CapturingWriter]:
    resolved: list[str] = []

    async def resolver(node: ResearchNode, budget: int) -> dict[str, Any]:
        resolved.append(node.node_id)
        return {"answered": True, "answer": f"answer for {node.node_id}", "tool_calls_used": 1}

    qa = SuggestingQA()
    writer = CapturingWriter()
    workflow = ResearchWorkflow(
        planner=StubPlanner(), lead=StubLead(), resolver=resolver, qa_reviewer=qa, writer=writer,
    )
    asyncio.run(workflow.run(run_id=uuid.uuid4().hex, query="routing test", caps=caps))
    return resolved, qa, writer


def test_final_qa_cycle_suggestions_are_resolved_before_writing():
    resolved, qa, writer = _run(RunCaps.for_strength(2))  # qa_cycles=1

    assert qa.review_calls == 1
    assert resolved == ["root", "gap1"]
    # The writer receives the gap node answered, not as a hollow record.
    assert writer.dag.nodes["gap1"].answer == "answer for gap1"
    assert writer.dag.nodes["gap1"].status == ResearchNodeStatus.ANSWERED


def test_each_qa_cycle_gets_its_own_resolution_pass():
    resolved, qa, writer = _run(RunCaps.for_strength(3))  # qa_cycles=2

    assert qa.review_calls == 2
    assert resolved == ["root", "gap1", "gap2"]
    assert writer.dag.nodes["gap2"].answer == "answer for gap2"


def test_zero_qa_cycles_still_goes_straight_to_write():
    resolved, qa, writer = _run(RunCaps.for_strength(1))  # qa_cycles=0

    assert qa.review_calls == 0
    assert resolved == ["root"]
    assert writer.dag is not None
