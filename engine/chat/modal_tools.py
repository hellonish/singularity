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
    # True only when a Sandbox actually ran the requested command and captured
    # its output — including non-zero exits from the user's own program. Left
    # False for web tools and for Sandbox failures that never reached execution
    # (provisioning, clone, timeout), so a code-level error still counts as
    # verified evidence the model may react to, while infra failures do not.
    executed: bool = False


class ChatToolExecutor(Protocol):
    async def execute(self, invocation: ChatToolInvocation) -> ChatToolResult: ...


class ModalToolExecutor:
    """The CLI-side client; it never forwards Groq or user credentials."""

    def __init__(self, function_lookup: Callable[[], Any] | None = None) -> None:
        self._function_lookup = function_lookup
        self._client = None
        self._function = None
        self._initialization_lock = asyncio.Lock()

    async def _get_function(self):
        if self._function is not None:
            return self._function
        async with self._initialization_lock:
            # Multiple research nodes start concurrently. Recheck under the
            # lock so they share one Modal client instead of each opening a
            # channel before the first lookup completes.
            if self._function is not None:
                return self._function
            if self._function_lookup is not None:
                self._function = self._function_lookup()
                return self._function
            import modal

            self._client = await modal.Client.from_env.aio()
            self._function = modal.Function.from_name(
                os.getenv("SINGULARITY_MODAL_APP", "singularity-chat-tools"),
                os.getenv("SINGULARITY_MODAL_FUNCTION", "execute_chat_tool"),
                environment_name=modal_environment_name(),
                client=self._client,
            )
            return self._function

    async def aclose(self) -> None:
        client = self._client
        # Drop object references before closing the transport.  A Function
        # handle can otherwise keep the gRPC channel alive past the end of a
        # short terminal turn and surface an opaque "Unclosed connection".
        self._client = None
        self._function = None
        try:
            if client is not None and not client.is_closed:
                await client.__aexit__.aio(None, None, None)
        except Exception:
            # Transport teardown is best-effort and must never replace the
            # actual tool result with an SDK-internal cleanup detail.
            pass

    async def execute(self, invocation: ChatToolInvocation) -> ChatToolResult:
        validated = validate_chat_tool_invocation(invocation)
        if TOOL_REGISTRY.descriptor(validated.tool_name).execution_kind != "trusted_function":
            raise ValueError(f"{validated.tool_name} is not a trusted Modal Function operation")
        function = await self._get_function()
        async with asyncio.timeout(validated.timeout_seconds):
            raw = await function.remote.aio(validated.payload())
        return ChatToolResult(
            content=str(raw.get("content", "")),
            sources=list(raw.get("sources", [])),
            credibility_base=float(raw.get("credibility_base", 0.0)),
            error=raw.get("error"),
        )
