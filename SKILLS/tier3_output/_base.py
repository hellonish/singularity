"""
BaseOutputSkill — shared pattern for all LLM-based tier-3 output skills.

Subclass this and set:
  - name        : str
  - PROMPT_FILE : str
  - format_type : str (matches OutputFormat literal: "report", "exec_summary", etc.)

It fetches LLM output (which is JSON) and converts it to an OutputDocument.
"""
import json
from pathlib import Path
from typing import Any

from orchestrator.skills import SkillBase
from orchestrator.models import NodeStatus, PlanNode
from contracts.skill_contracts import OutputDocument, OutputFormat
from context.budget import ContextBudgetManager

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_budget = ContextBudgetManager()


class BaseOutputSkill(SkillBase):
    name: str = "base_output"
    PROMPT_FILE: str = ""
    format_type: OutputFormat = "report"

    async def run(self, node: PlanNode, ctx, client, registry) -> tuple[Any, NodeStatus, float]:
        prompt_path = _PROMPTS_DIR / self.PROMPT_FILE
        if not prompt_path.exists():
            return self._fail(f"Prompt file not found: {self.PROMPT_FILE}")

        system_prompt = prompt_path.read_text(encoding="utf-8")
        upstream = _budget.build_context(node, ctx)

        user_message = (
            f"## Node\n"
            f"node_id: {node.node_id}\n"
            f"skill: {node.skill}\n"
            f"description: {node.description}\n"
            f"audience: {ctx.results.get('metadata', {}).get('audience', 'general')}\n\n"
            f"## Upstream Context\n{upstream}"
        )

        try:
            raw = client.generate_text(
                prompt=user_message,
                system_prompt=system_prompt,
                temperature=0.3, # Slightly more creative for outputs
            )
        except Exception as exc:
            return self._fail(f"LLM call failed: {exc}")

        try:
            data = self._extract_json(raw)
            
            # Combine findings into a single content string
            content_parts = []
            for item in data.get("findings", []):
                for k, v in item.items():
                    if isinstance(v, list):
                        content_parts.append(f"**{k}**\\n" + "\\n".join(f"- {x}" for x in v))
                    elif isinstance(v, dict):
                        content_parts.append(f"**{k}**\\n" + json.dumps(v, indent=2))
                    else:
                        content_parts.append(f"**{k}**\\n{v}")
                        
            content = "\\n\\n".join(content_parts)
            
            output = OutputDocument(
                skill_name=self.name,
                format=self.format_type,
                content=content,
                audience=ctx.results.get("metadata", {}).get("audience", "general"),
                word_count=0, # Auto-computed by pydantic validator
                citations_included=data.get("citations_used", []),
                coverage_gaps_disclosed=data.get("coverage_gaps", []),
                disclaimer_present=False,
                language=ctx.language,
            )
        except Exception as exc:
            return self._fail(f"Failed to parse LLM response: {exc}")

        status = NodeStatus.OK if float(data.get("confidence", 0.5)) >= 0.70 else NodeStatus.PARTIAL
        return output.to_dict(), status, float(data.get("confidence", 0.5))

    @staticmethod
    def _extract_json(text: str) -> dict:
        import re
        m = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))

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
            "content": f"FAILED: {error}",
        }, NodeStatus.FAILED, 0.0
