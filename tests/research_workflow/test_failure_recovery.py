import asyncio

from engine.research_workflow.caps import RunCaps
from engine.research_workflow.dag import ResearchDAG, ResearchNode, ResearchNodeStatus
from engine.research_workflow.runtime import resolve_frontier


def test_resolver_failure_is_terminal_not_stuck_running():
    caps = RunCaps.for_strength(1)
    dag = ResearchDAG()
    dag.add_node(ResearchNode(node_id="n1", question="question", section_id="s1", level=0), caps)

    async def failing_resolver(node, budget):
        raise RuntimeError("network unavailable")

    asyncio.run(resolve_frontier(dag, failing_resolver, caps))
    assert dag.nodes["n1"].status == ResearchNodeStatus.FAILED
    assert "network unavailable" in (dag.nodes["n1"].last_error or "")


def test_interrupted_nodes_return_to_pending_within_retry_budget():
    caps = RunCaps.for_strength(1)
    dag = ResearchDAG(nodes={
        "n1": ResearchNode(node_id="n1", question="question", section_id="s1", level=0, status=ResearchNodeStatus.RUNNING, attempts=1)
    })
    assert dag.recover_interrupted_nodes() == ["n1"]
    assert dag.nodes["n1"].status == ResearchNodeStatus.PENDING
