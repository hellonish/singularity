"""
fallback_router — internal orchestrator skill.
Never planned explicitly; used by FallbackRouter when primary skill fails.
"""
from orchestrator.skills import SkillBase
from orchestrator.models import NodeStatus


class FallbackRouterSkill(SkillBase):
    name = "fallback_router"

    async def run(self, node, ctx, client, registry):
        return {
            "skill_name": self.name,
            "summary": "Fallback router — internal skill, should not be called directly",
            "findings": [],
            "citations_used": [],
            "confidence": 0.0,
            "coverage_gaps": ["internal-only skill"],
            "upstream_slots_consumed": [],
        }, NodeStatus.SKIPPED, 0.0
