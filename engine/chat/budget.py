"""Fail-closed message-list budgeting against live provider model limits."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import tiktoken

from engine.llm.groq import GroqModel

CHAT_FORMAT_OVERHEAD_TOKENS = 64
CONTEXT_SAFETY_TOKENS = 256
MIN_OUTPUT_TOKENS = 64
TRUNCATION_MARKER = "\n\n[...context truncated to fit the model window...]\n\n"

# When over budget, oldest tool payloads are compacted to this many characters
# (head + tail around a truncation marker) before conversation context shrinks.
TOOL_COMPACT_KEEP_CHARS = 800

_CONTEXT_BLOCK = re.compile(r"(?s)(<context>\n)(.*?)(\n</context>)")


class ChatInputTooLarge(ValueError):
    pass


class ModelLimitsUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class BudgetedAgentMessages:
    messages: tuple[dict[str, Any], ...]
    input_token_upper_bound: int
    max_output_tokens: int
    compacted: bool


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


def budget_agent_messages(
    *,
    messages: list[dict[str, Any]],
    model: GroqModel,
    requested_output_tokens: int,
) -> BudgetedAgentMessages:
    """Fit one model turn's message list into the live model window.

    Compaction order preserves answer quality: oldest tool payloads shrink
    first (citations survive at the tail), then the `<context>` block in the
    first user message, and only then the output-token budget. The system
    prompt, the user message itself, and message *structure* (every assistant
    tool_calls entry keeps its tool replies) are never dropped, so the list
    always remains protocol-valid.
    """
    if not model.active:
        raise ModelLimitsUnavailable(f"model {model.id} is inactive")
    if not model.context_window or not model.max_completion_tokens:
        raise ModelLimitsUnavailable(f"provider did not return limits for model {model.id}")

    counter = TokenCounter(model.id)
    requested_output = min(requested_output_tokens, model.max_completion_tokens)
    working = [dict(message) for message in messages]
    compacted = False
    max_input_tokens = model.context_window - CONTEXT_SAFETY_TOKENS - requested_output

    if count_messages(working, counter) > max_input_tokens:
        compacted = _compact_tool_messages(working, counter, max_input_tokens) or compacted
    if count_messages(working, counter) > max_input_tokens:
        compacted = _shrink_context_block(working, counter, max_input_tokens) or compacted

    total = count_messages(working, counter)
    max_output_tokens = requested_output
    if total > max_input_tokens:
        # Everything compressible is compressed; spend output budget last.
        max_output_tokens = model.context_window - CONTEXT_SAFETY_TOKENS - total
        if max_output_tokens < MIN_OUTPUT_TOKENS:
            raise ChatInputTooLarge("context cannot be reduced enough to fit the selected model")
        compacted = True

    return BudgetedAgentMessages(
        messages=tuple(working),
        input_token_upper_bound=total,
        max_output_tokens=max_output_tokens,
        compacted=compacted,
    )


def count_messages(messages: list[dict[str, Any]], counter: TokenCounter) -> int:
    return CHAT_FORMAT_OVERHEAD_TOKENS + sum(_count_message(message, counter) for message in messages)


def _count_message(message: dict[str, Any], counter: TokenCounter) -> int:
    total = counter.count(str(message.get("role", ""))) + counter.count(str(message.get("content") or ""))
    tool_calls = message.get("tool_calls")
    if tool_calls:
        total += counter.count(json.dumps(tool_calls, ensure_ascii=False, sort_keys=True))
    return total


def _compact_tool_messages(
    working: list[dict[str, Any]],
    counter: TokenCounter,
    max_input_tokens: int,
) -> bool:
    changed = False
    for message in working:
        if message.get("role") != "tool":
            continue
        content = str(message.get("content") or "")
        if len(content) <= TOOL_COMPACT_KEEP_CHARS:
            continue
        message["content"] = _head_tail(content, TOOL_COMPACT_KEEP_CHARS)
        changed = True
        if count_messages(working, counter) <= max_input_tokens:
            break
    return changed


def _shrink_context_block(
    working: list[dict[str, Any]],
    counter: TokenCounter,
    max_input_tokens: int,
) -> bool:
    index = next((i for i, message in enumerate(working) if message.get("role") == "user"), None)
    if index is None:
        return False
    content = str(working[index].get("content") or "")
    match = _CONTEXT_BLOCK.search(content)
    if match is None:
        return False
    inner = match.group(2)

    def with_inner(candidate: str) -> str:
        return content[: match.start(2)] + candidate + content[match.end(2) :]

    low, high = 0, len(inner)
    best = ""
    while low <= high:
        keep = (low + high) // 2
        working[index]["content"] = with_inner(_head_tail(inner, keep))
        if count_messages(working, counter) <= max_input_tokens:
            best = _head_tail(inner, keep)
            low = keep + 1
        else:
            high = keep - 1
    working[index]["content"] = with_inner(best)
    return True


def _head_tail(text: str, keep: int) -> str:
    if keep >= len(text):
        return text
    if keep <= 0:
        return ""
    head = max(1, keep * 2 // 3)
    tail = max(0, keep - head)
    return text[:head] + TRUNCATION_MARKER + (text[-tail:] if tail else "")
