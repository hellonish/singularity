"""Modal adapter for validated, trusted chat tool calls."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from engine.tools.contracts import ChatToolInvocation, validate_chat_tool_invocation
from engine.tools import TOOL_REGISTRY


def modal_environment_name() -> str:
    """Resolve the Modal environment, defaulting to the account's real one.

    The default is intentionally "main": the previous "dev" default silently
    routed lookups to a non-existent environment whenever
    SINGULARITY_MODAL_ENVIRONMENT was unset (e.g. the CLI launched outside the
    repo root, so .env never loaded).
    """
    return os.getenv("SINGULARITY_MODAL_ENVIRONMENT", "main")


@dataclass(frozen=True)
class ChatToolResult:
    content: str
    sources: list[dict[str, Any]]
    credibility_base: float
    error: str | None


class ChatToolExecutor(Protocol):
    async def execute(self, invocation: ChatToolInvocation) -> ChatToolResult: ...


class ModalToolExecutor:
    """The CLI-side client; it never forwards Groq or user credentials."""

    def __init__(self, function_lookup: Callable[[], Any] | None = None) -> None:
        self._function_lookup = function_lookup or self._lookup_deployed_function

    @staticmethod
    def _lookup_deployed_function():
        import modal

        return modal.Function.from_name(
            os.getenv("SINGULARITY_MODAL_APP", "singularity-chat-tools"),
            os.getenv("SINGULARITY_MODAL_FUNCTION", "execute_chat_tool"),
            environment_name=modal_environment_name(),
        )

    async def execute(self, invocation: ChatToolInvocation) -> ChatToolResult:
        validated = validate_chat_tool_invocation(invocation)
        if TOOL_REGISTRY.descriptor(validated.tool_name).execution_kind != "trusted_function":
            raise ValueError(f"{validated.tool_name} is not a trusted Modal Function operation")
        function = self._function_lookup()
        async with asyncio.timeout(validated.timeout_seconds):
            raw = await function.remote.aio(validated.payload())
        return ChatToolResult(
            content=str(raw.get("content", "")),
            sources=list(raw.get("sources", [])),
            credibility_base=float(raw.get("credibility_base", 0.0)),
            error=raw.get("error"),
        )
