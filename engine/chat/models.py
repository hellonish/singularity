from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ChatAgentInput:
    """The complete public input contract for the chat agent."""

    context: str
    message: str

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("message must not be empty")


@dataclass(frozen=True)
class ChatStreamEvent:
    type: Literal["progress", "started", "delta", "completed"]
    model_id: str
    delta: str | None = None
    content: str | None = None
    input_token_upper_bound: int | None = None
    max_output_tokens: int | None = None
    context_truncated: bool = False
    progress_kind: str | None = None
    message: str | None = None
    elapsed_seconds: float | None = None
