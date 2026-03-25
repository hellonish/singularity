"""
Executor — FallbackRouter wraps skills with retry + chain logic.
execute_node and execute_wave drive the actual DAG execution.
"""
import asyncio
from typing import Any

from .config import CREDIBILITY_ADJ, RETRY_BACKOFF
from .context import ExecutionContext
from .domain import DomainRegistry
from .models import NodeStatus, PlanNode
from .skills import SkillBase


class FallbackRouter:
    """Tries the primary skill, then its fallback chain, with per-attempt retries."""

    def __init__(self, registry: DomainRegistry, skill_map: dict[str, SkillBase]):
        self._registry = registry
        self._skills = skill_map

    async def execute(
        self,
        node: PlanNode,
        ctx: ExecutionContext,
        client,
    ) -> tuple[Any, NodeStatus, float, str]:
        """Returns (result, status, credibility, fallback_level)."""
        chain = [node.skill] + self._registry.get_fallback_chain(node.skill)
        last_error: str | None = None

        for attempt_idx, skill_name in enumerate(chain[:3]):
            skill = self._skills.get(skill_name)
            if skill is None:
                last_error = f"skill '{skill_name}' not registered"
                continue

            for retry in range(len(RETRY_BACKOFF) + 1):
                try:
                    result, status, credibility = await skill.run(node, ctx, client, self._registry)
                except Exception as exc:
                    last_error = str(exc)
                    if retry < len(RETRY_BACKOFF):
                        await asyncio.sleep(RETRY_BACKOFF[retry])
                    continue

                if status != NodeStatus.FAILED:
                    fallback_level = "primary" if attempt_idx == 0 else f"fallback_{attempt_idx}"
                    if skill_name in CREDIBILITY_ADJ:
                        credibility = max(0.0, credibility + CREDIBILITY_ADJ[skill_name])
                    return result, status, credibility, fallback_level

                # Skill returned FAILED — try next in chain without retrying
                last_error = (result.get("error") or "skill returned FAILED") if isinstance(result, dict) else "skill returned FAILED"
                break

        return (
            {"error": last_error, "skill_attempted": chain[:3], "fallback_attempted": True},
            NodeStatus.FAILED,
            0.0,
            "exhausted",
        )


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
