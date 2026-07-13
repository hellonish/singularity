from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from .caps import RunCaps
from .dag import ResearchDAG, ResearchNode, ResearchNodeStatus

Resolver = Callable[[ResearchNode, int], Awaitable[dict[str, Any]]]


class ResearchCancelled(RuntimeError):
    """Raised by an execution adapter after it observes a durable cancellation."""


class ResearchInfrastructureError(RuntimeError):
    """Raised when the research backend itself is unreachable (e.g. Modal is
    down or unresponsive), as opposed to an individual search returning no
    results. It aborts the whole run so the user sees a "system busy" message
    instead of an empty report assembled from zero evidence."""

    user_message = "The research system is busy right now. Please try again in a few minutes."


async def resolve_frontier(dag: ResearchDAG, resolver: Resolver, caps: RunCaps) -> list[str]:
    """Resolve the dependency-ready frontier with bounded concurrency."""
    ready = dag.ready_nodes()
    semaphore = asyncio.Semaphore(caps.max_parallel_research_calls)

    async def resolve(node: ResearchNode) -> str:
        async with semaphore:
            node.status = ResearchNodeStatus.RUNNING
            node.attempts += 1
            try:
                result = await resolver(node, caps.max_tool_calls_per_node)
            except ResearchCancelled:
                node.status = ResearchNodeStatus.CANCELLED
                raise
            except ResearchInfrastructureError:
                # The backend is down, not just this query. Abort the whole
                # run rather than marking every node "failed" and assembling an
                # empty report.
                node.status = ResearchNodeStatus.FAILED
                raise
            except Exception as exc:
                node.status = ResearchNodeStatus.FAILED
                node.last_error = f"{type(exc).__name__}: {exc}"[:2_000]
                return node.node_id
            node.tool_calls_used = int(result.get("tool_calls_used", 0))
            if node.tool_calls_used > caps.max_tool_calls_per_node:
                node.status = ResearchNodeStatus.FAILED
                node.last_error = "resolver exceeded the four-call tool budget"
                return node.node_id
            node.answer_id = result.get("answer_id")
            node.answer = str(result.get("answer") or "") or None
            node.evidence_ids = list(result.get("evidence_ids", []))
            node.source_records = list(result.get("source_records", []))
            node.unresolved_gaps = list(result.get("unresolved_gaps", []))
            node.status = ResearchNodeStatus.ANSWERED if result.get("answered", True) else ResearchNodeStatus.FAILED
            return node.node_id

    return await asyncio.gather(*(resolve(node) for node in ready)) if ready else []
