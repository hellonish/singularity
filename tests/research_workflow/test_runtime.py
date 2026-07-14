import asyncio

from engine.research_workflow.caps import RunCaps
from engine.research_workflow.dag import ResearchDAG, ResearchNode
from engine.research_workflow.runtime import resolve_frontier


def test_frontier_resolver_passes_the_strength_scaled_call_budget():
    caps = RunCaps.for_strength(2)
    dag = ResearchDAG()
    dag.add_node(ResearchNode(node_id="root", question="Root", section_id="s1", level=0), caps)
    calls = []

    async def resolver(node, budget):
        calls.append((node.node_id, budget))
        return {"answered": True, "answer_id": f"a:{node.node_id}", "tool_calls_used": budget}

    asyncio.run(resolve_frontier(dag, resolver, caps))
    assert all(budget == caps.max_tool_calls_per_node for _, budget in calls)
