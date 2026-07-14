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
    ChatEffort.INSTANT: ChatEffortProfile(ChatEffort.INSTANT, 2, 700, 4_000, 2, 3, 1, 1, 20, 0.55, "low"),
    ChatEffort.MEDIUM: ChatEffortProfile(ChatEffort.MEDIUM, 6, 1_300, 12_000, 5, 6, 5, 2, 60, 0.70, "medium"),
    ChatEffort.HIGH: ChatEffortProfile(ChatEffort.HIGH, 12, 2_000, 24_000, 8, 10, 10, 5, 180, 0.80, "high"),
    ChatEffort.ULTRA: ChatEffortProfile(ChatEffort.ULTRA, 18, 3_000, 48_000, 15, 20, 20, 8, 420, 0.88, "high"),
}


def get_chat_effort_profile(effort: ChatEffort | str) -> ChatEffortProfile:
    return _PROFILES[ChatEffort(effort)]


def is_reasoning_model(model_id: str) -> bool:
    normalized = model_id.lower()
    return any(marker in normalized for marker in ("gpt-oss", "deepseek-r1", "/r1", "reasoning", "thinking"))


def reasoning_effort_for_model(model_id: str, effort: ChatEffort | str) -> str | None:
    if not is_reasoning_model(model_id):
        return None
    return get_chat_effort_profile(effort).reasoning_effort


def chat_output_budget(model_id: str, requested: int) -> int:
    """Reserve room for reasoning plus visible text on reasoning models."""
    return max(1_200, requested) if is_reasoning_model(model_id) else requested


# Conservative per-provider output ceilings used only when the selected model's
# live ``max_completion_tokens`` is unknown. These are floors-of-safety, not the
# providers' true maxima: a model may allow more, but we never exceed these
# without live confirmation so a request can't be rejected for over-allocating.
_PROVIDER_OUTPUT_CEILING: dict[str, int] = {
    "groq": 8_000,
    "deepseek": 8_000,
    "openrouter": 4_096,
}
_DEFAULT_PROVIDER_OUTPUT_CEILING = 4_096


def provider_output_budget(
    provider: str,
    model_id: str,
    requested: int,
    *,
    model_max_completion_tokens: int | None = None,
) -> int:
    """Resolve the output-token budget for one request against provider limits.

    Precedence:
    1. Start from ``requested`` (the effort budget), applying the reasoning-model
       floor so reasoning tokens don't starve the visible answer.
    2. If the selected model's live ``max_completion_tokens`` is known, clamp to
       it — the model's own limit is authoritative.
    3. Otherwise clamp to a static per-provider ceiling as a safe fallback.

    Shared by the CLI and API so both derive an identical budget from the same
    provider/model selection.
    """
    budget = chat_output_budget(model_id, requested)
    if model_max_completion_tokens is not None and model_max_completion_tokens > 0:
        ceiling = model_max_completion_tokens
    else:
        ceiling = _PROVIDER_OUTPUT_CEILING.get(provider, _DEFAULT_PROVIDER_OUTPUT_CEILING)
    return min(budget, ceiling)
