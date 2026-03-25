"""
BaseAnalysisSkill — shared pattern for all LLM-based tier-2 analysis skills.

Subclass this and set:
  - name        : str           (skill name matching SKILL_REGISTRY key)
  - PROMPT_FILE : str           (filename in prompts/ directory)

Override _parse_findings() if your skill needs custom finding extraction.
The default implementation already handles the standard AnalysisOutput shape.
"""
import json
from pathlib import Path
from typing import Any

from orchestrator.skills import SkillBase
from orchestrator.models import NodeStatus, PlanNode
from contracts.skill_contracts import AnalysisOutput
from context.budget import ContextBudgetManager


_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_budget = ContextBudgetManager()


class BaseAnalysisSkill(SkillBase):
    name: str = "base_analysis"
    PROMPT_FILE: str = ""   # e.g. "synthesis.md"

    # ------------------------------------------------------------------
    # Main entry — override run() only for non-LLM skills
    # ------------------------------------------------------------------

    async def run(self, node: PlanNode, ctx, client, registry) -> tuple[Any, NodeStatus, float]:
        # 1. Load system prompt
        prompt_path = _PROMPTS_DIR / self.PROMPT_FILE
        if not prompt_path.exists():
            return self._fail(f"Prompt file not found: {self.PROMPT_FILE}")

        system_prompt = prompt_path.read_text(encoding="utf-8")

        # 2. Build upstream context via budget manager
        upstream = _budget.build_context(node, ctx)

        # 3. Build user message
        user_message = (
            f"## Node\n"
            f"node_id: {node.node_id}\n"
            f"skill: {node.skill}\n"
            f"description: {node.description}\n"
            f"acceptance_axes: {', '.join(node.acceptance)}\n\n"
            f"## Upstream Context\n{upstream}"
        )

        # 4. Call LLM — use generate_text, then parse JSON
        try:
            raw = client.generate_text(
                prompt=user_message,
                system_prompt=system_prompt,
                temperature=0.3,
            )
        except Exception as exc:
            return self._fail(f"LLM call failed: {exc}")

        # 5. Parse into AnalysisOutput
        try:
            data = self._extract_json(raw)
            upstream_slots = list(ctx.results.keys())
            output = AnalysisOutput(
                skill_name=self.name,
                summary=data.get("summary", ""),
                findings=data.get("findings", []),
                citations_used=data.get("citations_used", []),
                confidence=float(data.get("confidence", 0.5)),
                coverage_gaps=data.get("coverage_gaps", []),
                upstream_slots_consumed=data.get("upstream_slots_consumed", upstream_slots),
            )
        except Exception as exc:
            return self._fail(f"Failed to parse LLM response: {exc}")

        # 6. Determine status
        status = NodeStatus.OK if output.confidence >= 0.70 else NodeStatus.PARTIAL
        return output.to_dict(), status, output.confidence

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract a JSON object from LLM output (handles code fences + trailing text)."""
        import re
        # Try code-fenced JSON first
        m = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))

        # Try raw_decode for leading JSON
        stripped = text.strip()
        if stripped.startswith("{"):
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(stripped)
            return obj

        raise ValueError(f"No JSON found in response (first 200 chars): {stripped[:200]}")

    @staticmethod
    def _fail(error: str) -> tuple[dict, NodeStatus, float]:
        return {
            "error": error,
            "summary": f"FAILED: {error}",
            "findings": [],
            "citations_used": [],
            "confidence": 0.0,
            "coverage_gaps": [error],
        }, NodeStatus.FAILED, 0.0
