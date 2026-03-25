"""
credibility_score — deterministic aggregation of upstream credibility.
Does NOT use an LLM — reads ctx.credibility_scores directly.
"""
from orchestrator.skills import SkillBase
from orchestrator.models import NodeStatus


class CredibilityScoreSkill(SkillBase):
    name = "credibility_score"

    async def run(self, node, ctx, client, registry):
        scores = list(ctx.credibility_scores.values())
        avg = sum(scores) / len(scores) if scores else 0.85

        result = {
            "skill_name": self.name,
            "summary": (
                f"Upstream credibility avg: {avg:.2f} — "
                + ("High confidence" if avg >= 0.80 else
                   "Moderate confidence" if avg >= 0.65 else
                   "Low confidence — flag heavily")
            ),
            "findings": [{
                "upstream_credibility_avg": round(avg, 3),
                "conflict_of_interest_flag": avg < 0.75,
                "scores_by_slot": dict(ctx.credibility_scores),
            }],
            "citations_used": [],
            "confidence": avg,
            "coverage_gaps": [],
            "upstream_slots_consumed": list(ctx.credibility_scores.keys()),
        }
        status = NodeStatus.OK if avg >= 0.65 else NodeStatus.PARTIAL
        return result, status, avg
