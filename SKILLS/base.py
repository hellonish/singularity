"""SkillBase — abstract base class for all skills."""
from typing import Any

from models import NodeStatus, PlanNode


class SkillBase:
    name: str = "base"

    async def run(
        self,
        node: PlanNode,
        ctx,
        client,
        registry,
    ) -> tuple[Any, NodeStatus, float]:
        raise NotImplementedError
