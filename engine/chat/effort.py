"""Chat effort profiles shared by CLI and future API chat execution."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ChatEffort(StrEnum):
    INSTANT = "instant"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


@dataclass(frozen=True)
class ChatEffortProfile:
    effort: ChatEffort
    max_agent_tool_steps: int
    max_output_tokens: int
    max_recent_raw_context_tokens: int
    max_old_messages: int
    max_document_chunks: int
    max_files: int
    max_calls_per_tool_type: int
    timeout_seconds: int
    compaction_trigger_percent: float
    reasoning_effort: str


_PROFILES = {
    ChatEffort.INSTANT: ChatEffortProfile(ChatEffort.INSTANT, 1, 500, 4_000, 2, 3, 1, 1, 20, 0.55, "low"),
    ChatEffort.MEDIUM: ChatEffortProfile(ChatEffort.MEDIUM, 4, 1_500, 12_000, 5, 6, 5, 2, 60, 0.70, "medium"),
    ChatEffort.HIGH: ChatEffortProfile(ChatEffort.HIGH, 8, 3_000, 24_000, 8, 10, 10, 5, 180, 0.80, "high"),
    ChatEffort.ULTRA: ChatEffortProfile(ChatEffort.ULTRA, 12, 6_000, 48_000, 15, 20, 20, 8, 420, 0.88, "high"),
}


def get_chat_effort_profile(effort: ChatEffort | str) -> ChatEffortProfile:
    return _PROFILES[ChatEffort(effort)]


def reasoning_effort_for_model(model_id: str, effort: ChatEffort | str) -> str | None:
    if model_id not in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}:
        return None
    return get_chat_effort_profile(effort).reasoning_effort
