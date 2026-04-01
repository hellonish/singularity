"""
Thinker — the reasoning layer that sits between user input and execution.

Given a user message + conversation history, the Thinker:
  1. Decides the mode: "chat" (1-5 steps) or "research" (5-10 steps)
  2. Selects relevant skills from the registry (0-3 for chat, any for research)
  3. Produces an ordered step plan

The plan is shown to the user BEFORE any execution begins, making the
agent fully transparent.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from skills import SKILL_DOCS


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ThinkStep(BaseModel):
    step_id: int
    type: str            # "direct_answer" | "web_search" | "skill_call" | "analyze" | "summarize"
    description: str
    skill_name: str | None = None   # must be a key in SKILL_REGISTRY, or None


class ThinkPlan(BaseModel):
    mode: str                        # "chat" | "research"
    reasoning: str                   # Brief explanation of why this mode/plan
    selected_skills: list[str]       # Subset of skills the agent will touch
    steps: list[ThinkStep]
    strength: int = 5                # 1-10; only meaningful for research mode
    audience: str = "practitioner"   # layperson / student / practitioner / expert / executive


# ---------------------------------------------------------------------------
# System prompt — loaded from thinker_system_prompt.md, then formatted with
# the skill menu sourced live from each skill's skill.md.
# SKILL_DOCS parses USE/NOT hints from skill.md at import time so the thinker
# always reflects the current skill documentation without manual upkeep.
# ---------------------------------------------------------------------------

_THINKER_SYSTEM: str = (
    (Path(__file__).parent / "thinker_system_prompt.md")
    .read_text(encoding="utf-8")
    .format(skill_menu=SKILL_DOCS.thinker_menu())
)


# ---------------------------------------------------------------------------
# Thinker
# ---------------------------------------------------------------------------

class Thinker:
    """
    Calls an LLM to produce a ThinkPlan for a given user message.
    """

    def __init__(self, client) -> None:
        self._client = client

    def think(
        self,
        message: str,
        history: list[dict[str, str]],
        extended: bool = False,
    ) -> ThinkPlan:
        """
        Synchronous call — returns a ThinkPlan.

        Args:
            message:   The latest user message.
            history:   List of {"role": "user"|"assistant", "content": "..."}.
                       Last 5 turns max (caller's responsibility to trim).
            extended:  Whether extended thinking mode is active (allows research).
        """
        history_block = ""
        if history:
            lines = []
            for turn in history[-5:]:
                role = turn["role"].upper()
                content = turn["content"][:300]  # truncate long turns
                lines.append(f"[{role}]: {content}")
            history_block = "\nConversation history (last 5 turns):\n" + "\n".join(lines) + "\n"

        extended_note = (
            "\nNOTE: Extended thinking is ACTIVE. You may use research mode for complex questions "
            "and increase step count up to 10.\n"
            if extended else ""
        )

        prompt = (
            f"{history_block}"
            f"{extended_note}"
            f"\nUser message: {message}\n\n"
            "Produce a ThinkPlan JSON object."
        )

        return self._client.generate_structured(
            prompt=prompt,
            system_prompt=_THINKER_SYSTEM,
            schema=ThinkPlan,
            temperature=0.3,
            max_tokens=1500,
        )
