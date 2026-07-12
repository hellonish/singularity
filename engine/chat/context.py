"""Context-layer contracts and the universal token policy for chat."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UniversalContextPolicy:
    """Deterministic, model-aware limits shared by every chat conversation."""

    safety_tokens: int = 256
    summary_trigger_ratio: float = 0.50
    minimum_summary_trigger_tokens: int = 512
    maximum_summary_trigger_tokens: int = 8_192
    summary_output_ratio: float = 0.20
    maximum_summary_output_tokens: int = 1_500

    def usable_input_tokens(self, *, context_window: int, reserved_output_tokens: int) -> int:
        usable = context_window - reserved_output_tokens - self.safety_tokens
        if usable <= 0:
            raise ValueError("model context window cannot accommodate the requested output and safety margin")
        return usable

    def summary_trigger_tokens(self, *, context_window: int, reserved_output_tokens: int) -> int:
        usable = self.usable_input_tokens(
            context_window=context_window,
            reserved_output_tokens=reserved_output_tokens,
        )
        return min(
            usable,
            self.maximum_summary_trigger_tokens,
            max(self.minimum_summary_trigger_tokens, int(usable * self.summary_trigger_ratio)),
        )

    def summary_output_cap_tokens(self, *, context_window: int, reserved_output_tokens: int) -> int:
        usable = self.usable_input_tokens(
            context_window=context_window,
            reserved_output_tokens=reserved_output_tokens,
        )
        return min(self.maximum_summary_output_tokens, max(1, int(usable * self.summary_output_ratio)))


@dataclass(frozen=True)
class ReportContext:
    report_id: str
    version_id: str
    version_number: int
    checksum: str
    content: str


@dataclass(frozen=True)
class SummaryContext:
    id: str
    sequence: int
    through_message_id: str | None
    through_message_sequence: int
    content: str
    token_count: int | None


@dataclass(frozen=True)
class ContextTurn:
    id: str
    sequence: int
    role: str
    content: str


@dataclass(frozen=True)
class ContextSnapshot:
    """The durable inputs selected for one LLM response."""

    chat_id: str
    report: ReportContext | None
    summary: SummaryContext | None
    turns: tuple[ContextTurn, ...]
    latest_message_id: str | None

