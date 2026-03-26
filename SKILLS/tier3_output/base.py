"""
BaseOutputSkill — shared pattern for all LLM-based tier-3 output skills.

Subclass this and set:
  - name        : str
  - PROMPT_FILE : str  (kept for compat, but prompt.md is loaded from skill's own dir)
  - format_type : str (matches OutputFormat literal: "report", "exec_summary", etc.)

It fetches LLM output (which is JSON) and converts it to an OutputDocument.
"""
import asyncio
import importlib
import json
from pathlib import Path
from typing import Any

from skills.base import SkillBase
from models import NodeStatus, PlanNode, OutputDocument, OutputFormat
from context.budget import ContextBudgetManager

_budget = ContextBudgetManager()


class BaseOutputSkill(SkillBase):
    name: str = "base_output"
    PROMPT_FILE: str = ""  # kept for compat; actual prompt loaded from skill dir
    format_type: OutputFormat = "report"

    async def run(self, node: PlanNode, ctx, client, registry) -> tuple[Any, NodeStatus, float]:
        # Load system prompt from the skill's own directory
        skill_module = importlib.import_module(type(self).__module__)
        prompt_path = Path(skill_module.__file__).parent / "prompt.md"
        if not prompt_path.exists():
            return self._fail(f"Prompt file not found: {prompt_path}")

        system_prompt = prompt_path.read_text(encoding="utf-8")
        upstream = _budget.build_context(node, ctx)

        audience = getattr(ctx, "audience", "") or ctx.results.get("metadata", {}).get("audience", "general")
        user_message = (
            f"## Node\n"
            f"node_id: {node.node_id}\n"
            f"skill: {node.skill}\n"
            f"description: {node.description}\n"
            f"audience: {audience}\n\n"
            f"## Upstream Context\n{upstream}"
        )

        try:
            # Use asyncio.to_thread so the sync HTTP call doesn't block the event loop
            raw = await asyncio.to_thread(
                client.generate_text,
                prompt=user_message,
                system_prompt=system_prompt,
                temperature=0.3,
            )
        except Exception as exc:
            return self._fail(f"LLM call failed: {exc}")

        try:
            data = self._extract_json(raw)

            # Build proper Markdown sections from findings list
            sections: list[str] = []
            summary = data.get("summary", "")
            if summary:
                sections.append(f"## Executive Summary\n\n{summary}")
            for item in data.get("findings", []):
                title = item.get("section", "")
                body = item.get("content", "") or item.get("explanation", "")
                if not body:
                    # Fallback: serialize any non-section string/list values
                    extra_parts = []
                    for k, v in item.items():
                        if k == "section":
                            continue
                        if isinstance(v, list):
                            extra_parts.append("\n".join(f"- {x}" if not str(x).startswith("-") else str(x) for x in v))
                        elif isinstance(v, str):
                            extra_parts.append(v)
                    body = "\n\n".join(extra_parts)
                if title or body:
                    sections.append(f"## {title}\n\n{body}")

            content = "\n\n".join(sections)

            output = OutputDocument(
                skill_name=self.name,
                format=self.format_type,
                content=content,
                audience=audience,
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
