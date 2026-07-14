from __future__ import annotations

import operator
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypedDict

from .caps import RunCaps
from .dag import ResearchDAG
from engine.llm.groq import ProviderError


class ResearchGraphState(TypedDict, total=False):
    run_id: str
    original_query: str
    query: str
    polished_objective: dict[str, Any]
    cycle: int
    dag: dict[str, Any]
    caps: dict[str, Any]
    planner_proposals: list[dict[str, Any]]
    qa_reviews: Annotated[list[dict[str, Any]], operator.add]
    events: Annotated[list[dict[str, Any]], operator.add]
    report: dict[str, Any]
    stop_reason: str | None


def build_research_graph(*, planner, lead, resolver, qa_reviewer, writer, checkpointer=None, progress_reporter: Callable[[dict[str, Any]], Awaitable[None]] | None = None):
    """Build the production LangGraph parent graph.

    Imports are lazy so API schema/unit tests do not require the optional graph
    packages. Production startup fails with an actionable error if they are not
    installed.
    """
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover - exercised in deployment
        raise RuntimeError("install langgraph to run the research worker") from exc

    async def progress(phase: str, status: str, message: str, **details: Any) -> None:
        if progress_reporter is not None:
            await progress_reporter({"phase": phase, "status": status, "message": message, **details})

    async def polish(state: ResearchGraphState):
        await progress("planning", "started", "Clarifying research objective")
        polished = await planner.polish_prompt(state["query"])
        await progress("planning", "completed", "Research objective ready")
        return {
            "original_query": state["query"],
            "query": polished.get("query", state["query"]),
            "polished_objective": polished,
            "events": [{"kind": "prompt_polished"}],
        }

    async def planners(state: ResearchGraphState):
        await progress(
            "planning",
            "started",
            "Generating independent research angles",
            planners=getattr(planner, "max_perspectives", 1),
        )
        proposals = await planner.parallel_proposals(state["query"])
        await progress("planning", "completed", "Research angles ready", planners=len(proposals))
        return {"planner_proposals": proposals, "events": [{"kind": "planners_completed"}]}

    async def lead_node(state: ResearchGraphState):
        await progress("planning", "started", "Building bounded research plan")
        dag = await lead.merge(state["query"], state["planner_proposals"], RunCaps(**state["caps"]))
        await progress("planning", "completed", "Research plan ready", node_count=len(dag.nodes))
        return {"dag": dag.model_dump(), "events": [{"kind": "lead_completed"}]}

    async def resolve(state: ResearchGraphState):
        await progress("researching", "started", "Researching planned questions")
        from .runtime import resolve_frontier
        dag = ResearchDAG.model_validate(state["dag"])
        await resolve_frontier(dag, resolver, RunCaps(**state["caps"]))
        await progress("researching", "completed", "Research pass complete")
        return {"dag": dag.model_dump(), "events": [{"kind": "research_frontier_completed"}]}

    async def qa(state: ResearchGraphState):
        dag = ResearchDAG.model_validate(state["dag"])
        caps = RunCaps(**state["caps"])
        cycle = int(state.get("cycle", 0)) + 1
        await progress("reviewing", "started", f"Reviewing source coverage — cycle {cycle}", cycle=cycle)
        try:
            reviews = await qa_reviewer.review(dag, caps)
        except (ProviderError, TimeoutError, ValueError) as exc:
            # QA improves coverage but should not discard successfully
            # retrieved and synthesized evidence when a provider fails.
            reviews = [{"section_id": "all", "passed": None, "gaps": [], "skipped": True}]
            await progress(
                "reviewing",
                "skipped",
                "Coverage review skipped after provider failure; continuing with completed evidence",
                cycle=cycle,
                error_type=type(exc).__name__,
            )
        else:
            await progress("reviewing", "completed", f"Coverage review complete — cycle {cycle}", cycle=cycle)
        return {
            "dag": dag.model_dump(),
            "qa_reviews": reviews,
            "cycle": int(state.get("cycle", 0)) + 1,
            "events": [{"kind": "qa_completed", "cycle": int(state.get("cycle", 0)) + 1}],
        }

    async def write(state: ResearchGraphState):
        await progress("writing", "started", "Writing sourced research report")
        report = await writer.write(
            ResearchDAG.model_validate(state["dag"]),
            state["query"],
            RunCaps(**state["caps"]),
        )
        await progress("writing", "completed", "Research report written")
        return {"report": report, "events": [{"kind": "report_written"}]}

    def route_after_qa(state: ResearchGraphState):
        # Any gap-filling nodes QA just accepted must be researched before
        # writing — including those from the final QA cycle, which previously
        # went straight to the writer as permanently unanswered nodes.
        dag = ResearchDAG.model_validate(state["dag"])
        return "resolve" if dag.ready_nodes() else "write"

    def route_after_research(state: ResearchGraphState):
        # The cycle count gates QA passes (not resolve passes), so each QA
        # pass's suggestions get exactly one resolution round and the run
        # performs exactly caps.qa_cycles reviews.
        if int(state.get("cycle", 0)) < RunCaps(**state["caps"]).qa_cycles:
            return "qa"
        return "write"

    graph = StateGraph(ResearchGraphState)
    graph.add_node("polish_prompt", polish)
    graph.add_node("parallel_planners", planners)
    graph.add_node("plan_lead", lead_node)
    graph.add_node("resolve_frontier", resolve)
    graph.add_node("qa_sections", qa)
    graph.add_node("write_report", write)
    graph.add_edge(START, "polish_prompt")
    graph.add_edge("polish_prompt", "parallel_planners")
    graph.add_edge("parallel_planners", "plan_lead")
    graph.add_edge("plan_lead", "resolve_frontier")
    graph.add_conditional_edges("resolve_frontier", route_after_research, {"qa": "qa_sections", "write": "write_report"})
    graph.add_conditional_edges("qa_sections", route_after_qa, {"resolve": "resolve_frontier", "write": "write_report"})
    graph.add_edge("write_report", END)
    return graph.compile(checkpointer=checkpointer)
