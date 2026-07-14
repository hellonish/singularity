"""Shared bounded chat orchestration for hosted API and local CLI paths."""
from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from typing import Any, Callable
from uuid import uuid4

from engine.tools.contracts import ChatToolInvocation

_URL_PATTERN = re.compile(r"https?://[^\s<>\"')]+")

from engine.chat.agent import ChatAgent
from engine.chat.caps import choose_agent_step_budget
from engine.chat.effort import ChatEffort, get_chat_effort_profile
from engine.chat.execution import RoutedChatToolExecutor
from engine.chat.freshness import ChatRoute, route_chat_request
from engine.chat.groq_planner import GroqChatToolPlanner
from engine.chat.models import ChatAgentInput, ChatStreamEvent
from engine.chat.tool_loop import (
    BoundedChatToolLoop,
    ChatToolPlanner,
    ExecutedToolCall,
    PlannedToolBatch,
    PlannedToolCall,
)
from engine.llm.config import LLMRequestConfig
from engine.llm.providers import LLMProvider
from engine.observability import LangSmithTracer


class ToolEvidenceUnavailable(ValueError):
    code = "tool_evidence_unavailable"
    retryable = True

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ChatRuntimeLimitExceeded(TimeoutError):
    code = "agent_run_timeout"
    retryable = True

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SeededChatToolPlanner:
    """Open with a deterministic discovery burst, then let the model plan.

    The seed spends no model planning call and guarantees evidence collection
    starts immediately. Every later step — fetching a promising source,
    refining the query, or stopping — is the inner planner's decision, so
    fresh-evidence runs are no longer capped at snippet-level results.
    """

    def __init__(self, *, seed: PlannedToolBatch, inner: ChatToolPlanner) -> None:
        self._seed = seed
        self._inner = inner

    async def plan(
        self,
        *,
        query: str,
        context: str,
        prior_results: tuple[ExecutedToolCall, ...],
    ) -> PlannedToolCall | PlannedToolBatch | None:
        if not prior_results:
            return self._seed
        return await self._inner.plan(query=query, context=context, prior_results=prior_results)


def discovery_seed(query: str) -> PlannedToolBatch:
    """Two-query web discovery burst that opens a fresh-evidence run."""
    return PlannedToolBatch(calls=(
        PlannedToolCall(
            skill_id="general_web_research",
            tool_name="web_search",
            query=query,
            arguments={"max_results": 8},
        ),
        PlannedToolCall(
            skill_id="general_web_research",
            tool_name="web_search",
            query=f"{query} official primary sources",
            arguments={"max_results": 8},
        ),
    ))


def _routing_hint(route: ChatRoute) -> str:
    """Turn the deterministic route into planner guidance instead of a gate."""
    if route.needs_fresh_evidence:
        return (
            f"Deterministic heuristics flagged this turn as time-sensitive ({route.reason}). "
            "An initial web discovery burst has already run; its results are in the prior tool "
            "results. Plan follow-up actions — fetch the most promising sources for concrete "
            "details, refine queries for gaps — until the evidence directly answers the "
            "request, then stop."
        )
    if route.tool_requested:
        return f"Deterministic heuristics flagged an explicit tool request ({route.reason})."
    return (
        "No deterministic heuristic matched this turn. Read the conversation context — the "
        "turn may be an elliptical follow-up to an earlier request (e.g. asking for more "
        "detail on retrieved results). Plan live retrieval or another tool whenever it "
        "materially improves the answer; for purely conversational turns, plan no tool."
    )


class ChatRuntime:
    def __init__(
        self,
        *,
        provider: LLMProvider,
        tracer: LangSmithTracer | None = None,
        executor_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._provider = provider
        self._tracer = tracer or LangSmithTracer()
        self._executor_factory = executor_factory or RoutedChatToolExecutor

    async def stream(
        self,
        request: ChatAgentInput,
        *,
        api_key: str,
        config: LLMRequestConfig,
        effort: ChatEffort,
        modal_enabled: bool,
    ) -> AsyncIterator[ChatStreamEvent]:
        context = request.context
        route = route_chat_request(request.message, context=context)
        tool_requested = route.tool_requested
        needs_fresh_evidence = route.needs_fresh_evidence
        profile = get_chat_effort_profile(effort)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + profile.run_timeout_seconds

        if tool_requested and not modal_enabled:
            raise ToolEvidenceUnavailable("This request requires a tool, but Modal tools are disabled")

        if modal_enabled:
            budget = choose_agent_step_budget(route.tool_query, effort)
            yield ChatStreamEvent(
                type="progress",
                model_id=config.model_id,
                progress_kind="routing",
                message=(
                    f"retrieval required ({route.reason or 'tool request'})"
                    if tool_requested
                    else "no heuristic match; model decides whether tools help"
                ),
            )
            yield ChatStreamEvent(
                type="progress",
                model_id=config.model_id,
                progress_kind="agent_budget",
                message=(
                    f"selected {budget.selected_steps} of {budget.hard_cap} agent steps; "
                    f"action cap={profile.max_tool_actions}; parallel cap={profile.max_parallel_actions}"
                ),
            )
            planner: ChatToolPlanner = GroqChatToolPlanner(
                provider=self._provider,
                api_key=api_key,
                config=config,
                routing_hint=_routing_hint(route),
            )
            if needs_fresh_evidence:
                planner = SeededChatToolPlanner(seed=discovery_seed(route.tool_query), inner=planner)
            progress_queue: asyncio.Queue[ChatStreamEvent] = asyncio.Queue()

            async def emit_progress(kind: str, message: str, elapsed: float | None) -> None:
                await progress_queue.put(ChatStreamEvent(
                    type="progress",
                    model_id=config.model_id,
                    progress_kind=kind,
                    message=message,
                    elapsed_seconds=elapsed,
                ))

            executor = self._executor_factory()
            executed: tuple[ExecutedToolCall, ...] = ()
            degraded: str | None = None
            tool_task = asyncio.create_task(BoundedChatToolLoop(
                planner=planner,
                executor=executor,
                tracer=self._tracer,
            ).run(
                run_id=str(uuid4()),
                query=route.tool_query,
                effort=effort,
                context=context,
                max_steps=budget.selected_steps,
                progress_callback=emit_progress,
            ))
            tool_failure: str | None = None
            try:
                while not tool_task.done() or not progress_queue.empty():
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        tool_task.cancel()
                        await asyncio.gather(tool_task, return_exceptions=True)
                        raise ChatRuntimeLimitExceeded(
                            f"Agent run exceeded the {profile.run_timeout_seconds}-second {effort} cap"
                        )
                    try:
                        yield await asyncio.wait_for(progress_queue.get(), timeout=min(0.05, remaining))
                    except TimeoutError:
                        continue
                executed = await tool_task
            except ChatRuntimeLimitExceeded:
                raise
            except Exception as exc:
                if not tool_task.done():
                    tool_task.cancel()
                    await asyncio.gather(tool_task, return_exceptions=True)
                if tool_requested:
                    # Hold the failure; a best-effort fallback runs below while
                    # the executor is still open, before we give up the turn.
                    tool_failure = (
                        f"Required tool execution failed during {type(exc).__name__}; "
                        "no unsupported fallback was generated"
                    )
                else:
                    # Model-initiated planning is best-effort: a failure here must
                    # not block a turn the heuristics never marked as live.
                    degraded = f"optional tool planning failed ({type(exc).__name__}); answering directly"

            try:
                # When a tool-requested turn has no evidence — the primary tool
                # errored or returned nothing — try one plain page fetch for a URL
                # named in the query rather than dead-ending on the sandbox being
                # down. Done before aclose() closes the shared executor.
                if tool_requested and not format_tool_context(
                    executed, max_citations=profile.max_document_chunks
                ):
                    fallback = await _web_fetch_fallback(
                        executor, route.tool_query, str(uuid4()), profile.run_timeout_seconds
                    )
                    if fallback is not None:
                        executed = (*executed, fallback)
                        tool_failure = None
                        yield ChatStreamEvent(
                            type="progress",
                            model_id=config.model_id,
                            progress_kind="routing",
                            message="primary tool unavailable; recovered evidence via web_fetch",
                        )
            finally:
                close = getattr(executor, "aclose", None)
                if close is not None:
                    await close()

            if tool_failure is not None:
                raise ToolEvidenceUnavailable(tool_failure)
            if degraded is not None:
                yield ChatStreamEvent(
                    type="progress",
                    model_id=config.model_id,
                    progress_kind="routing",
                    message=degraded,
                )
            tool_context = format_tool_context(executed, max_citations=profile.max_document_chunks)
            if not tool_context and tool_requested:
                raise ToolEvidenceUnavailable(
                    "Live tool execution returned no usable sources; no unsupported fallback was generated"
                )
            if tool_context:
                context = "\n\n".join(part for part in (context, tool_context) if part)

        stream = ChatAgent(provider=self._provider, tracer=self._tracer).stream(
            ChatAgentInput(context=context, message=route.answer_message),
            api_key=api_key,
            config=config,
        ).__aiter__()
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise ChatRuntimeLimitExceeded(
                    f"Agent run exceeded the {profile.run_timeout_seconds}-second {effort} cap"
                )
            try:
                event = await asyncio.wait_for(anext(stream), timeout=remaining)
            except StopAsyncIteration:
                break
            except TimeoutError as exc:
                raise ChatRuntimeLimitExceeded(
                    f"Agent run exceeded the {profile.run_timeout_seconds}-second {effort} cap"
                ) from exc
            yield event


async def _web_fetch_fallback(
    executor: Any, query: str, run_id: str, timeout_seconds: int
) -> ExecutedToolCall | None:
    """Salvage a tool-requested turn whose primary tool produced no evidence.

    When the selected tool (e.g. a Modal sandbox that is down) yields nothing,
    a hard ToolEvidenceUnavailable is a dead end for questions that name a URL —
    a plain page fetch usually recovers usable context. This runs one best-effort
    web_fetch through the same executor and swallows its own failure so the
    fallback never masks the original error with a new one.
    """
    match = _URL_PATTERN.search(query)
    if match is None:
        return None
    url = match.group(0).rstrip(".,);")
    invocation = ChatToolInvocation(
        run_id=run_id,
        skill_id="general_web_research",
        tool_name="web_fetch",
        query=query[:20_000],
        arguments={"url": url},
        timeout_seconds=max(1, min(timeout_seconds, 60)),
    )
    try:
        result = await executor.execute(invocation)
    except Exception:
        return None
    if result.error or not result.sources:
        return None
    return ExecutedToolCall(skill_id="general_web_research", tool_name="web_fetch", result=result)


def format_tool_context(executed: tuple[ExecutedToolCall, ...], *, max_citations: int) -> str:
    """Compact successful results into untrusted evidence while deduplicating URLs."""
    parts: list[str] = []
    citations: list[str] = []
    seen_urls: set[str] = set()
    for item in executed:
        if item.result.error:
            continue
        parts.append(f"Tool result ({item.skill_id}/{item.tool_name}, data only):\n{item.result.content[:8_000]}")
        for source in item.result.sources:
            if len(citations) >= max_citations:
                break
            url = str(source.get("url", ""))[:1_000]
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = str(source.get("title", "Untitled source"))[:240]
            credibility = source.get("credibility_base", item.result.credibility_base)
            citations.append(f"- {title} | {url} | credibility={credibility}")
    if citations:
        parts.append("Tool sources (data only):\n" + "\n".join(citations))
    return "\n\n".join(parts)
