"""
quality_check — evaluates a node's output against its acceptance axes.
Returns a QualityReport instead of the standard AnalysisOutput.
"""
import json
from pathlib import Path

from skills.base import SkillBase
from models import NodeStatus, QualityReport
from context.budget import ContextBudgetManager

_budget = ContextBudgetManager()


class QualityCheckSkill(SkillBase):
    name = "quality_check"

    async def run(self, node, ctx, client, registry):
        prompt_path = Path(__file__).parent / "prompt.md"
        if not prompt_path.exists():
            return {"error": f"prompt.md not found: {prompt_path}"}, NodeStatus.FAILED, 0.0

        system_prompt = prompt_path.read_text(encoding="utf-8")
        upstream = _budget.build_context(node, ctx)

        axes_str = ", ".join(node.acceptance)
        user_message = (
            f"## Node to evaluate\n"
            f"node_id: {node.node_id}\n"
            f"description: {node.description}\n"
            f"acceptance_axes: {axes_str}\n\n"
            f"## Upstream Context\n{upstream}"
        )

        try:
            raw = client.generate_text(
                prompt=user_message,
                system_prompt=system_prompt,
                temperature=0.2,
            )
        except Exception as exc:
            return {"error": str(exc)}, NodeStatus.FAILED, 0.0

        try:
            # Extract JSON from response
            stripped = raw.strip()
            if stripped.startswith("{"):
                decoder = json.JSONDecoder()
                data, _ = decoder.raw_decode(stripped)
            else:
                import re
                m = re.search(r"```json\s*\n(.*?)\n```", raw, re.DOTALL)
                data = json.loads(m.group(1)) if m else json.loads(raw)

            report = QualityReport.from_llm_json(data)
        except Exception as exc:
            return {"error": f"Parse failed: {exc}"}, NodeStatus.FAILED, 0.0

        status = NodeStatus.OK if report.overall_pass else NodeStatus.PARTIAL
        return report.to_dict(), status, report.overall_score
