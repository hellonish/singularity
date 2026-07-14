"""Policy-enforced dispatch across trusted Modal Functions and Sandboxes."""
from __future__ import annotations

from typing import Callable

from engine.chat.modal_sandbox import ModalSandboxExecutor
from engine.chat.modal_tools import ChatToolExecutor, ChatToolResult, ModalToolExecutor
from engine.chat.retry import RetryPolicy, retry_async
from engine.tools import TOOL_REGISTRY
from engine.tools.contracts import ChatToolInvocation


class RoutedChatToolExecutor:
    def __init__(
        self,
        *,
        trusted: ChatToolExecutor | None = None,
        sandbox: ChatToolExecutor | None = None,
        trusted_factory: Callable[[], ChatToolExecutor] = ModalToolExecutor,
        sandbox_factory: Callable[[], ChatToolExecutor] = ModalSandboxExecutor,
    ) -> None:
        self._trusted = trusted
        self._sandbox = sandbox
        self._trusted_factory = trusted_factory
        self._sandbox_factory = sandbox_factory

    async def execute(self, invocation: ChatToolInvocation) -> ChatToolResult:
        kind = TOOL_REGISTRY.descriptor(invocation.tool_name).execution_kind
        if kind == "trusted_function":
            if self._trusted is None:
                self._trusted = self._trusted_factory()
            return await retry_async(
                lambda: self._trusted.execute(invocation),
                policy=RetryPolicy(max_retries=2),
            )
        if kind == "sandbox":
            if self._sandbox is None:
                self._sandbox = self._sandbox_factory()
            return await retry_async(
                lambda: self._sandbox.execute(invocation),
                policy=RetryPolicy(max_retries=1),
            )
        raise ValueError(f"{invocation.tool_name} is API-only and cannot be dispatched by the chat planner")

    async def aclose(self) -> None:
        for executor in (self._trusted, self._sandbox):
            close = getattr(executor, "aclose", None)
            if close is not None:
                await close()
