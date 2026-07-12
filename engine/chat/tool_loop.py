"""Bounded, skill-scoped tool planning for Chat mode."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol

from engine.chat.effort import ChatEffort, get_chat_effort_profile
from engine.chat.modal_tools import ChatToolExecutor, ChatToolResult
from engine.observability import LangSmithTracer
from engine.tools.contracts import ChatToolInvocation, validate_chat_tool_invocation


@dataclass(frozen=True)
class PlannedToolCall:
    skill_id: str
    tool_name: str
    query: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ExecutedToolCall:
    skill_id: str
    tool_name: str
    result: ChatToolResult


class ChatToolPlanner(Protocol):
    async def plan(
        self,
        *,
        query: str,
        context: str,
        prior_results: tuple[ExecutedToolCall, ...],
    ) -> PlannedToolCall | None: ...


class BoundedChatToolLoop:
    def __init__(
        self,
        *,
        planner: ChatToolPlanner,
        executor: ChatToolExecutor,
        tracer: LangSmithTracer | None = None,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._tracer = tracer or LangSmithTracer()

    async def run(
        self,
        *,
        run_id: str,
        query: str,
        effort: ChatEffort,
        context: str,
        progress_callback: Callable[[str, str, float | None], Awaitable[None]] | None = None,
    ) -> tuple[ExecutedToolCall, ...]:
        profile = get_chat_effort_profile(effort)
        calls_by_tool: dict[str, int] = {}
        completed: list[ExecutedToolCall] = []
        async with asyncio.timeout(profile.timeout_seconds):
            for _ in range(profile.max_agent_tool_steps):
                if progress_callback is not None:
                    await progress_callback("thinking", "", None)
                async with self._tracer.span(
                    "tool_planning",
                    inputs={"query": self._tracer.text(query)},
                    metadata={"prior_result_count": len(completed)},
                    tags=["chat", "tool-planning"],
                ) as span:
                    planned = await self._planner.plan(
                        query=query,
                        context=context,
                        prior_results=tuple(completed),
                    )
                    span.end({"planned": planned.tool_name if planned else None})
                if planned is None:
                    break
                if calls_by_tool.get(planned.tool_name, 0) >= profile.max_calls_per_tool_type:
                    break
                invocation = ChatToolInvocation(
                    run_id=run_id,
                    skill_id=planned.skill_id,
                    tool_name=planned.tool_name,
                    query=planned.query,
                    arguments=planned.arguments,
                    effort=effort,
                    timeout_seconds=profile.timeout_seconds,
                )
                # Validate at the orchestration boundary as well as in the
                # executor/remote Function. This guarantees that alternate
                # executors cannot accidentally dispatch untrusted arguments.
                validate_chat_tool_invocation(invocation)
                started_at = asyncio.get_running_loop().time()
                if progress_callback is not None:
                    await progress_callback("tool_start", f"{planned.skill_id}/{planned.tool_name}", None)
                async with self._tracer.span(
                    f"modal_tool:{planned.skill_id}/{planned.tool_name}",
                    run_type="tool",
                    inputs={"query": self._tracer.text(planned.query)},
                    metadata={
                        "skill_id": planned.skill_id,
                        "tool_name": planned.tool_name,
                        "effort": str(effort),
                    },
                    tags=["chat", "modal", "tool"],
                ) as span:
                    result = await self._executor.execute(invocation)
                    span.end({"success": result.error is None, "source_count": len(result.sources)})
                elapsed = asyncio.get_running_loop().time() - started_at
                calls_by_tool[planned.tool_name] = calls_by_tool.get(planned.tool_name, 0) + 1
                if progress_callback is not None:
                    await progress_callback(
                        "tool_failed" if result.error else "tool_completed",
                        f"{planned.skill_id}/{planned.tool_name}",
                        elapsed,
                    )
                completed.append(
                    ExecutedToolCall(
                        skill_id=planned.skill_id,
                        tool_name=planned.tool_name,
                        result=_redact_result(result),
                    )
                )
        return tuple(completed)


def _redact_result(result: ChatToolResult) -> ChatToolResult:
    """Keep generated prompt context from echoing credential-like values."""
    import re

    redact = re.compile(r"(?i)(api[_-]?key|apikey|token|authorization)(=|:|%3d)\s*([^&\s'\"]+)")

    def redact_value(value: Any) -> Any:
        if isinstance(value, str):
            return redact.sub(r"\1\2[REDACTED]", value)
        if isinstance(value, list):
            return [redact_value(item) for item in value]
        if isinstance(value, dict):
            return {key: redact_value(item) for key, item in value.items()}
        return value

    return ChatToolResult(
        content=redact.sub(r"\1\2[REDACTED]", result.content),
        sources=redact_value(result.sources),
        credibility_base=result.credibility_base,
        error=redact.sub(r"\1\2[REDACTED]", result.error or "") or None,
    )
