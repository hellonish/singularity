"""
BaseOutputSkill — shared pattern for all LLM-based tier-3 output skills.

Subclass this and set:
  - name        : str           (skill name matching SKILL_REGISTRY key)
  - format_type : str           (matches OutputFormat literal: "report", "exec_summary", etc.)

The system prompt is loaded from ``prompt.md`` in the skill's own directory at
runtime via ``importlib.__file__``.  Subclasses do not need to declare a prompt
path; just place ``prompt.md`` next to ``skill.py``.
"""
import asyncio
import importlib
import json
import textwrap
from pathlib import Path
from typing import Any

from skills.base import SkillBase
from models import NodeStatus, PlanNode, OutputDocument, OutputFormat


MAX_DIRECT_CHARS: int = 12000
MAX_INDIRECT_CHARS: int = 350
MAX_TOTAL_CHARS: int = 32000


def _is_direct_dep(slot: str, direct_ids: set[str]) -> bool:
    for node_id in direct_ids:
        if node_id in slot or slot in node_id:
            return True
    return False


def _extract_summary(result: Any, raw: str) -> str:
    if isinstance(result, dict):
        for key in ("summary", "synthesis", "report", "explainer"):
            value = result.get(key)
            if isinstance(value, str):
                return textwrap.shorten(value, width=MAX_INDIRECT_CHARS)
    return textwrap.shorten(raw, width=MAX_INDIRECT_CHARS)


def _build_upstream_context(node: PlanNode, ctx) -> str:
    """Build a bounded upstream context string for generic output skills."""
    direct_ids = set(node.depends_on)
    sections: list[tuple[str, str, float, bool]] = []

    for slot, result in ctx.results.items():
        cred = ctx.credibility_scores.get(slot, 0.5)
        raw = result if isinstance(result, str) else json.dumps(result, default=str)
        direct = _is_direct_dep(slot, direct_ids)
        text = raw[:MAX_DIRECT_CHARS] if direct else _extract_summary(result, raw)
        sections.append((slot, text, cred, direct))

    sections.sort(key=lambda item: (not item[3], -item[2]))

    parts: list[str] = []
    if node.synthesis_hint:
        parts.append(f"## Synthesis Hint\n{node.synthesis_hint}\n")

    total = sum(len(part) for part in parts)
    for slot, text, cred, _direct in sections:
        entry = f"## Upstream: {slot} (credibility={cred:.2f})\n{text}\n"
        if total + len(entry) > MAX_TOTAL_CHARS:
            remaining = MAX_TOTAL_CHARS - total
            if remaining > 100:
                parts.append(entry[:remaining] + "\n[...truncated]")
            break
        parts.append(entry)
        total += len(entry)

    return "\n".join(parts)


class BaseOutputSkill(SkillBase):
    """Base class for LLM-driven tier-3 skills.  Do not set ``name`` here;
    concrete subclasses must declare it to trigger auto-registration."""
    format_type: OutputFormat = "report"

    async def run(self, node: PlanNode, ctx, client, registry) -> tuple[Any, NodeStatus, float]:
        # Load system prompt from the skill's own directory
        skill_module = importlib.import_module(type(self).__module__)
        prompt_path = Path(skill_module.__file__).parent / "prompt.md"
        if not prompt_path.exists():
            return self._fail(f"Prompt file not found: {prompt_path}")

        system_prompt = prompt_path.read_text(encoding="utf-8")
        upstream = _build_upstream_context(node, ctx)

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
