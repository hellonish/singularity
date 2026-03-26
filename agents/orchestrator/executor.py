"""
Executor — execute_node and execute_wave drive the actual DAG execution.
"""
import asyncio

from models import NodeStatus, PlanNode, ExecutionContext
from .fallback_router import FallbackRouter


async def execute_node(
    node: PlanNode,
    ctx: ExecutionContext,
    client,
    router: FallbackRouter,
) -> None:
    result, status, credibility, fallback_level = await router.execute(node, ctx, client)
    ctx.record(node, result, status, credibility, fallback_level)
    tag = f"[{fallback_level}]" if fallback_level != "primary" else ""
    print(f"  [{status.value.upper()}]{tag} {node.node_id} → {node.output_slot}")


async def execute_wave(
    wave: list[PlanNode],
    ctx: ExecutionContext,
    client,
    router: FallbackRouter,
    wave_idx: int,
) -> None:
    pending    = [n for n in wave if not ctx.is_resolved(n.node_id)]
    parallel   = [n for n in pending if n.parallelizable]
    sequential = [n for n in pending if not n.parallelizable]

    if not pending:
        return

    print(f"\n  Wave {wave_idx}: {len(parallel)} parallel + {len(sequential)} sequential")
    if parallel:
        await asyncio.gather(*[execute_node(n, ctx, client, router) for n in parallel])
    for node in sequential:
        await execute_node(node, ctx, client, router)
