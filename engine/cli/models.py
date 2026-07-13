from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from engine.chat.effort import ChatEffort, get_chat_effort_profile


@dataclass(frozen=True)
class TerminalHistoryTurn:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class TerminalContextFile:
    path: Path
    content: str


@dataclass
class TerminalSession:
    api_key: str = ""
    credential_source: Literal["global_config", "runtime", "none"] = "none"
    provider: Literal["groq", "deepseek", "openrouter"] = "groq"
    model_id: str = "openai/gpt-oss-20b"
    agent_name: Literal["chat", "research"] = "chat"
    effort: ChatEffort = ChatEffort.MEDIUM
    context: str = ""
    context_source: str | None = None
    context_files: list[TerminalContextFile] = field(default_factory=list)
    history: list[TerminalHistoryTurn] = field(default_factory=list)
    compacted_summary: str | None = None
    # History remains append-only in this ephemeral session. This marker says
    # which prefix is represented by ``compacted_summary`` rather than deleting
    # the source turns, so a failed replacement cannot lose chat facts.
    compacted_through: int = 0
    temperature: float = 0.3
    max_output_tokens: int = 1_500

    def __post_init__(self) -> None:
        if self.api_key and self.credential_source == "none":
            self.credential_source = "runtime"
        self.apply_effort(self.effort)

    def apply_effort(self, effort: ChatEffort | str) -> None:
        self.effort = ChatEffort(effort)
        self.max_output_tokens = get_chat_effort_profile(self.effort).max_output_tokens


@dataclass(frozen=True)
class TerminalOutput:
    kind: Literal[
        "thinking",
        "tool_planning_start",
        "tool_planning_timeout",
        "tool_start",
        "tool_completed",
        "tool_failed",
        "model_started",
        "metadata",
        "delta",
        "completed",
    ]
    content: str
    elapsed_seconds: float | None = None
