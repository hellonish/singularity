"""Adaptive per-request budgets bounded by the selected effort profile."""
from __future__ import annotations

from dataclasses import dataclass

from engine.chat.effort import ChatEffort, get_chat_effort_profile
from engine.chat.freshness import requests_tool_use, requires_fresh_evidence


@dataclass(frozen=True)
class AgentStepBudget:
    selected_steps: int
    hard_cap: int
    reasons: tuple[str, ...]


def choose_agent_step_budget(query: str, effort: ChatEffort | str) -> AgentStepBudget:
    profile = get_chat_effort_profile(effort)
    normalized = " ".join(query.lower().split())
    selected = 2
    reasons: list[str] = ["base request understanding and verification"]

    if requests_tool_use(normalized):
        selected += 1
        reasons.append("tool execution")
    if requires_fresh_evidence(normalized):
        selected += 1
        reasons.append("fresh evidence")
    if any(term in normalized for term in ("multiple sources", "compare", "corroborate", "citations")):
        selected += 3
        reasons.append("multi-source synthesis")
    if any(term in normalized for term in ("write code", "execute", "run code", "implement", "script")):
        selected += 5
        reasons.append("code generation and execution")
    if any(term in normalized for term in ("debug", "fix", "failing", "error", "test")):
        selected += 2
        reasons.append("repair and test cycle")
    if any(term in normalized for term in ("verify", "validate", "double-check", "double check")):
        selected += 2
        reasons.append("explicit verification")

    return AgentStepBudget(
        selected_steps=max(1, min(profile.max_agent_tool_steps, selected)),
        hard_cap=profile.max_agent_tool_steps,
        reasons=tuple(reasons),
    )
