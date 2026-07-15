"""Full-skill catalog with progressive instruction disclosure for the agent loop."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from engine.skills import SKILL_REGISTRY
from engine.tools import TOOL_REGISTRY
from engine.tools.contracts import TOOL_ARGUMENT_MODELS

LOAD_SKILL_TOOL_NAME = "load_skill"

# Skills whose one-line summary is enough to use their tools correctly; the
# model is told it may call these without a load_skill round-trip.
NO_LOAD_SKILL_IDS = ("general_web_research",)

_CHAT_EXECUTION_KINDS = ("trusted_function", "sandbox")


@lru_cache(maxsize=1)
def chat_skill_ids() -> tuple[str, ...]:
    """Every skill exposing at least one chat-plannable tool contract."""
    ids: list[str] = []
    for skill in SKILL_REGISTRY.definitions():
        for tool_name in skill.config.tools:
            if TOOL_REGISTRY.descriptor(tool_name).execution_kind not in _CHAT_EXECUTION_KINDS:
                continue
            if tool_name not in TOOL_ARGUMENT_MODELS:
                continue
            ids.append(skill.id)
            break
    return tuple(sorted(ids))


@lru_cache(maxsize=1)
def skill_catalog_text() -> str:
    """One line per available skill for the agent system prompt."""
    lines: list[str] = []
    for skill_id in chat_skill_ids():
        skill = SKILL_REGISTRY.get(skill_id)
        tools = ", ".join(
            name
            for name in skill.config.tools
            if TOOL_REGISTRY.descriptor(name).execution_kind in _CHAT_EXECUTION_KINDS
            and name in TOOL_ARGUMENT_MODELS
        )
        lines.append(f"- {skill.id}: {skill.config.description} (tools: {tools})")
    no_load = ", ".join(NO_LOAD_SKILL_IDS)
    return (
        "Available skills (one line each):\n"
        + "\n".join(lines)
        + f"\n\nBefore first use of a specialized skill's tools, call {LOAD_SKILL_TOOL_NAME}"
        f"(skill_id) to receive its full instructions. {no_load} needs no loading."
    )


def load_skill_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": LOAD_SKILL_TOOL_NAME,
            "description": (
                "Load the full instructions and constraints for one listed skill "
                "before using its tools."
            ),
            "parameters": {
                "type": "object",
                "properties": {"skill_id": {"type": "string", "minLength": 1}},
                "required": ["skill_id"],
                "additionalProperties": False,
            },
        },
    }


def load_skill_instructions(skill_id: str) -> str:
    """Full instructions for one chat-available skill.

    Raises ``KeyError`` for unknown or chat-unavailable skills so the loop can
    reject the call with the valid id list.
    """
    if skill_id not in chat_skill_ids():
        raise KeyError(skill_id)
    skill = SKILL_REGISTRY.get(skill_id)
    return f"Skill {skill.id}:\n{skill.instructions}"
