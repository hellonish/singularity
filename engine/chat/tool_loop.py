"""Bounded, skill-scoped tool planning for Chat mode."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol

from engine.chat.effort import ChatEffort, get_chat_effort_profile
from engine.chat.modal_tools import ChatToolExecutor, ChatToolResult
from engine.observability import LangSmithTracer
from engine.tools.contracts import ChatToolInvocation, validate_chat_tool_invocation
from engine.tools import TOOL_REGISTRY

TOOL_PLANNING_TIMEOUT_SECONDS = 10


class ToolPlanningTimeout(TimeoutError):
    pass


class ToolExecutionTimeout(TimeoutError):
    pass


@dataclass(frozen=True)
class PlannedToolCall:
    skill_id: str
    tool_name: str
    query: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class PlannedToolBatch:
    calls: tuple[PlannedToolCall, ...]

    def __post_init__(self) -> None:
        if not self.calls:
            raise ValueError("planned tool batch must not be empty")


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
    ) -> PlannedToolCall | PlannedToolBatch | None: ...


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
        max_steps: int | None = None,
        progress_callback: Callable[[str, str, float | None], Awaitable[None]] | None = None,
    ) -> tuple[ExecutedToolCall, ...]:
        profile = get_chat_effort_profile(effort)
        calls_by_tool: dict[str, int] = {}
        completed: list[ExecutedToolCall] = []
        total_actions = 0
        step_limit = min(profile.max_agent_tool_steps, max_steps or profile.max_agent_tool_steps)
        for _ in range(step_limit):
            if progress_callback is not None:
                await progress_callback("tool_planning_start", "Selecting a tool", None)
            try:
                async with asyncio.timeout(TOOL_PLANNING_TIMEOUT_SECONDS):
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
                        span.end({
                            "planned": (
                                [call.tool_name for call in planned.calls]
                                if isinstance(planned, PlannedToolBatch)
                                else planned.tool_name if planned else None
                            )
                        })
            except TimeoutError as exc:
                if progress_callback is not None:
                    await progress_callback("tool_planning_timeout", "Tool planning timed out after 10s", None)
                if completed:
                    break
                raise ToolPlanningTimeout("Tool planning timed out after 10 seconds; no tool was dispatched") from exc
            if planned is None:
                break
            proposed = planned.calls if isinstance(planned, PlannedToolBatch) else (planned,)
            invocations: list[tuple[PlannedToolCall, ChatToolInvocation]] = []
            for call in proposed:
                if total_actions >= profile.max_tool_actions:
                    break
                per_tool_cap = (
                    profile.max_code_repair_cycles + 1
                    if call.tool_name == "code_execution"
                    else profile.max_calls_per_tool_type
                )
                if calls_by_tool.get(call.tool_name, 0) >= per_tool_cap:
                    continue
                arguments = dict(call.arguments)
                # One DDGS attempt per agent run. Every later general-web
                # discovery action goes directly to Tavily, including calls in
                # the same parallel burst.
                if call.tool_name == "web_search" and calls_by_tool.get(call.tool_name, 0) > 0:
                    arguments["search_backend"] = "tavily"
                invocation = ChatToolInvocation(
                    run_id=run_id,
                    skill_id=call.skill_id,
                    tool_name=call.tool_name,
                    query=call.query,
                    arguments=arguments,
                    effort=effort,
                    timeout_seconds=profile.timeout_seconds,
                )
                validate_chat_tool_invocation(invocation)
                calls_by_tool[call.tool_name] = calls_by_tool.get(call.tool_name, 0) + 1
                total_actions += 1
                invocations.append((call, invocation))
            if not invocations:
                break
            semaphore = asyncio.Semaphore(profile.max_parallel_actions)
            sandbox_semaphore = asyncio.Semaphore(profile.max_sandbox_workers)

            async def execute_one(call: PlannedToolCall, invocation: ChatToolInvocation) -> ExecutedToolCall:
                async with semaphore:
                    started_at = asyncio.get_running_loop().time()
                    tool_label = _format_tool_call(invocation)
                    if progress_callback is not None:
                        await progress_callback("tool_start", tool_label, None)
                    try:
                        async with self._tracer.span(
                            f"modal_tool:{call.skill_id}/{call.tool_name}",
                            run_type="tool",
                            inputs={"query": self._tracer.text(call.query)},
                            metadata={
                                "skill_id": call.skill_id,
                                "tool_name": call.tool_name,
                                "effort": str(effort),
                            },
                            tags=["chat", "modal", "tool"],
                        ) as span:
                            async with asyncio.timeout(profile.timeout_seconds):
                                if TOOL_REGISTRY.descriptor(call.tool_name).execution_kind == "sandbox":
                                    async with sandbox_semaphore:
                                        result = await self._executor.execute(invocation)
                                else:
                                    result = await self._executor.execute(invocation)
                            span.end({"success": result.error is None, "source_count": len(result.sources)})
                    except Exception as exc:
                        result = ChatToolResult(
                            content="",
                            sources=[],
                            credibility_base=0.0,
                            error=(
                                f"timed out after {profile.timeout_seconds} seconds"
                                if isinstance(exc, TimeoutError)
                                else f"{type(exc).__name__}: {exc}"
                            ),
                        )
                    elapsed = asyncio.get_running_loop().time() - started_at
                    if progress_callback is not None:
                        result_label = (
                            f"{tool_label} — {len(result.sources)} source(s)"
                            if not result.error
                            else tool_label
                        )
                        await progress_callback(
                            "tool_failed" if result.error else "tool_completed",
                            result_label,
                            elapsed,
                        )
                    return ExecutedToolCall(
                        skill_id=call.skill_id,
                        tool_name=call.tool_name,
                        result=_redact_result(result),
                    )

            completed.extend(await asyncio.gather(*(execute_one(call, invocation) for call, invocation in invocations)))
        return tuple(completed)


def _format_tool_call(invocation: ChatToolInvocation) -> str:
    """Render the validated invocation shown in the terminal lifecycle."""
    arguments = json.dumps(invocation.arguments, ensure_ascii=False, sort_keys=True, separators=(", ", ": "))
    query = invocation.query.replace("\n", " ")
    return f"{invocation.tool_name}(query={query!r}, arguments={arguments})"


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
