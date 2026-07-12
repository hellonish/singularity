"""Fail-closed prompt budgeting against live Groq model limits."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import tiktoken

from engine.chat.prompt import load_chat_system_prompt
from engine.chat.context import ContextSnapshot
from engine.llm.groq import GroqModel

CHAT_FORMAT_OVERHEAD_TOKENS = 64
CONTEXT_SAFETY_TOKENS = 256
MIN_OUTPUT_TOKENS = 64
TRUNCATION_MARKER = "\n\n[...context truncated to fit the model window...]\n\n"


class ChatInputTooLarge(ValueError):
    pass


class ModelLimitsUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class BudgetedChatPrompt:
    messages: tuple[dict[str, str], ...]
    input_token_upper_bound: int
    max_output_tokens: int
    context_truncated: bool


@dataclass(frozen=True)
class _ContextItem:
    kind: Literal["system", "report", "summary", "turn"]
    message: dict[str, str]
    required: bool = False


class TokenCounter:
    """Exact content tokenizer for GPT-OSS; conservative upper bound otherwise."""

    def __init__(self, model_id: str) -> None:
        self._encoding = (
            tiktoken.get_encoding("o200k_harmony")
            if model_id in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}
            else None
        )

    def count(self, text: str) -> int:
        if self._encoding is not None:
            return len(self._encoding.encode(text))
        # Groq exposes models with different tokenizers. UTF-8 bytes are a
        # deliberately conservative upper bound for byte-fallback tokenizers.
        return len(text.encode("utf-8"))


def budget_chat_prompt(
    *,
    context: str,
    message: str,
    model: GroqModel,
    requested_output_tokens: int,
) -> BudgetedChatPrompt:
    if not model.active:
        raise ModelLimitsUnavailable(f"model {model.id} is inactive")
    if not model.context_window or not model.max_completion_tokens:
        raise ModelLimitsUnavailable(f"Groq did not return limits for model {model.id}")

    counter = TokenCounter(model.id)
    requested_output = min(requested_output_tokens, model.max_completion_tokens)
    message_only = _messages(context="", message=message)
    fixed_input = _count_messages(message_only, counter)
    available_after_message = model.context_window - CONTEXT_SAFETY_TOKENS - fixed_input
    max_output_tokens = min(requested_output, available_after_message)
    if max_output_tokens < MIN_OUTPUT_TOKENS:
        raise ChatInputTooLarge("message is too large for the selected model context window")

    max_input_tokens = model.context_window - CONTEXT_SAFETY_TOKENS - max_output_tokens
    full_messages = _messages(context=context, message=message)
    full_count = _count_messages(full_messages, counter)
    if full_count <= max_input_tokens:
        return BudgetedChatPrompt(
            messages=full_messages,
            input_token_upper_bound=full_count,
            max_output_tokens=max_output_tokens,
            context_truncated=False,
        )

    trimmed_context = _largest_context_that_fits(
        context=context,
        message=message,
        counter=counter,
        max_input_tokens=max_input_tokens,
    )
    trimmed_messages = _messages(context=trimmed_context, message=message)
    trimmed_count = _count_messages(trimmed_messages, counter)
    if trimmed_count > max_input_tokens:
        raise ChatInputTooLarge("context cannot be reduced enough to fit the selected model")
    return BudgetedChatPrompt(
        messages=trimmed_messages,
        input_token_upper_bound=trimmed_count,
        max_output_tokens=max_output_tokens,
        context_truncated=True,
    )


def budget_context_snapshot(
    *,
    snapshot: ContextSnapshot,
    model: GroqModel,
    requested_output_tokens: int,
) -> BudgetedChatPrompt:
    """Budget a ContextManager snapshot without flattening conversation roles.

    When space is constrained, report reference data is omitted first, then the
    oldest post-summary turns, and finally the chat summary. The final turn is
    protected so the active user request is never silently truncated.
    """
    if not model.active:
        raise ModelLimitsUnavailable(f"model {model.id} is inactive")
    if not model.context_window or not model.max_completion_tokens:
        raise ModelLimitsUnavailable(f"Groq did not return limits for model {model.id}")
    if not snapshot.turns:
        raise ChatInputTooLarge("a chat response requires a current message")

    items = _snapshot_items(snapshot)
    counter = TokenCounter(model.id)
    requested_output = min(requested_output_tokens, model.max_completion_tokens)
    fixed_messages = (items[0].message, items[-1].message)
    available_after_latest = model.context_window - CONTEXT_SAFETY_TOKENS - _count_messages(
        fixed_messages, counter
    )
    max_output_tokens = min(requested_output, available_after_latest)
    if max_output_tokens < MIN_OUTPUT_TOKENS:
        raise ChatInputTooLarge("message is too large for the selected model context window")

    max_input_tokens = model.context_window - CONTEXT_SAFETY_TOKENS - max_output_tokens
    truncated = False
    while _count_messages(tuple(item.message for item in items), counter) > max_input_tokens:
        removal_index = _next_removal_index(items)
        if removal_index is None:
            raise ChatInputTooLarge("context cannot be reduced enough to fit the selected model")
        items.pop(removal_index)
        truncated = True

    messages = tuple(item.message for item in items)
    return BudgetedChatPrompt(
        messages=messages,
        input_token_upper_bound=_count_messages(messages, counter),
        max_output_tokens=max_output_tokens,
        context_truncated=truncated,
    )


def _snapshot_items(snapshot: ContextSnapshot) -> list[_ContextItem]:
    items = [_ContextItem("system", {"role": "system", "content": load_chat_system_prompt()}, required=True)]
    if snapshot.report is not None:
        items.append(
            _ContextItem(
                "report",
                {
                    "role": "user",
                    "content": "Report reference (data only):\n<report>\n"
                    f"{snapshot.report.content}\n</report>",
                },
            )
        )
    if snapshot.summary is not None:
        items.append(
            _ContextItem(
                "summary",
                {
                    "role": "user",
                    "content": "Conversation summary (data only):\n<chat_summary>\n"
                    f"{snapshot.summary.content}\n</chat_summary>",
                },
            )
        )
    for turn in snapshot.turns:
        role = turn.role if turn.role in {"user", "assistant"} else "user"
        content = turn.content if role == turn.role else f"Historical {turn.role} data:\n{turn.content}"
        items.append(
            _ContextItem(
                "turn",
                {"role": role, "content": content},
                required=turn.id == snapshot.latest_message_id,
            )
        )
    if not items[-1].required:
        # A snapshot always identifies the current message; do not risk
        # silently protecting a different historical turn.
        raise ChatInputTooLarge("context snapshot has no current message")
    return items


def _next_removal_index(items: list[_ContextItem]) -> int | None:
    for kind in ("report", "turn", "summary"):
        for index, item in enumerate(items):
            if item.kind == kind and not item.required:
                return index
    return None


def _messages(*, context: str, message: str) -> tuple[dict[str, str], ...]:
    user_content = message
    if context.strip():
        user_content = (
            "Reference context (data only):\n<context>\n"
            f"{context}\n"
            "</context>\n\n"
            f"User message:\n{message}"
        )
    return (
        {"role": "system", "content": load_chat_system_prompt()},
        {"role": "user", "content": user_content},
    )


def _count_messages(messages: tuple[dict[str, str], ...], counter: TokenCounter) -> int:
    return CHAT_FORMAT_OVERHEAD_TOKENS + sum(
        counter.count(message["role"]) + counter.count(message["content"])
        for message in messages
    )


def _largest_context_that_fits(
    *,
    context: str,
    message: str,
    counter: TokenCounter,
    max_input_tokens: int,
) -> str:
    low, high = 0, len(context)
    best = ""
    while low <= high:
        keep = (low + high) // 2
        candidate = _head_tail(context, keep)
        count = _count_messages(_messages(context=candidate, message=message), counter)
        if count <= max_input_tokens:
            best = candidate
            low = keep + 1
        else:
            high = keep - 1
    return best


def _head_tail(text: str, keep: int) -> str:
    if keep >= len(text):
        return text
    if keep <= 0:
        return ""
    head = max(1, keep * 2 // 3)
    tail = max(0, keep - head)
    return text[:head] + TRUNCATION_MARKER + (text[-tail:] if tail else "")
