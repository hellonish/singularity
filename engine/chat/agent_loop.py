"""Unified native tool-calling chat agent loop shared by the hosted API and CLI.

One model drives the whole turn: it plans tool calls natively (many per turn,
executed in parallel), sees results as ``role: "tool"`` messages, and streams
the final answer from the same loop. Effort profiles bound every dimension —
model turns, total and per-tool actions, parallelism, timeouts — while the
model decides what to do inside those bounds.
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field, replace
from typing import Any, Callable
from uuid import uuid4

from engine.chat.budget import budget_agent_messages
from engine.chat.catalog import (
    LOAD_SKILL_TOOL_NAME,
    NO_LOAD_SKILL_IDS,
    chat_skill_ids,
    load_skill_instructions,
    load_skill_schema,
    skill_catalog_text,
)
from engine.chat.capability_router import (
    repository_url as validated_repository_url,
    sandbox_enabled,
    select_capability,
    trusted_function_enabled,
)
from engine.chat.effort import ChatEffort, ChatEffortProfile, get_chat_effort_profile
from engine.chat.execution import RoutedChatToolExecutor
from engine.chat.freshness import ChatRoute, route_chat_request
from engine.chat.modal_tools import ChatToolResult
from engine.chat.model_capabilities import MODEL_CAPABILITIES, ModelCapabilityRegistry
from engine.chat.models import ChatAgentInput, ChatStreamEvent
from engine.chat.prompt import build_runtime_system_prompt
from engine.chat.retry import RetryPolicy
from engine.entity_resolution import (
    EntityScope,
    SourceEntityDecision,
    clarification_for_scope,
    classify_source,
    lightweight_chat_scope,
    scope_search_query,
)
from engine.llm.config import LLMRequestConfig
from engine.llm.groq import GroqProviderError, LLMStreamEvent, LLMToolCall
from engine.llm.providers import LLMProvider
from engine.observability import LangSmithTracer
from engine.tools import TOOL_REGISTRY
from engine.tools.contracts import (
    ChatToolInvocation,
    chat_planner_tool_schemas,
    validate_chat_tool_invocation,
)

TOOL_RESULT_MAX_CHARS = 8_000

_SEED_SKILL_ID = "general_web_research"
_SEED_FUNCTION_NAME = f"{_SEED_SKILL_ID}__web_search"

_ENTITY_RETRIEVAL_TOOLS = frozenset({
    "arxiv", "browser_render", "clinicaltrials", "courtlistener", "dataset_hub",
    "github", "google_books", "pdf_reader", "pubmed", "sec_edgar",
    "semantic_scholar", "standards_fetch", "web_fetch", "web_search",
    "youtube_transcript",
})

_RETRYABLE_ERROR_MARKERS = (
    "timed out", "timeout", "connection", "unavailable", "temporar", "rate limit", "cancelled",
)
_REDACT = re.compile(r"(?i)(api[_-]?key|apikey|token|authorization)(=|:|%3d)\s*([^&\s'\"]+)")

_FORCED_ANSWER_NOTE = (
    "Step or time budget exhausted. Do not request tools. Answer the user now "
    "from the evidence above; state explicitly what could not be verified."
)

_SANDBOX_DEGRADED_NOTE = (
    "The Sandbox could not run this request, so no execution result is "
    "available. Do not request tools and do not claim any output was produced "
    "or verified. Answer the user directly and helpfully: (1) state plainly, in "
    "one sentence, that you were not able to run it in the Sandbox this time; "
    "(2) provide the complete code or commands the user asked about so they can "
    "copy and run it themselves, in a fenced code block; (3) briefly explain "
    "what running it would produce or how to interpret the result; (4) point to "
    "a couple of concrete resources (docs, install steps, or references) that "
    "help them proceed. Keep the tone matter-of-fact, not apologetic."
)


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


@dataclass
class _LoopState:
    calls_by_tool: dict[str, int] = field(default_factory=dict)
    total_actions: int = 0
    loaded_skills: set[str] = field(default_factory=set)
    sandbox_evidence_succeeded: bool = False
    approved_repository_url: str | None = None
    gpu_authorized: bool = False


@dataclass(frozen=True)
class _TurnResult:
    text: str
    tool_calls: tuple[LLMToolCall, ...]


def classify_tool_error(error: str) -> str:
    """Type a tool failure so the model can choose retry, alternate, or disclose."""
    lowered = error.lower()
    if any(marker in lowered for marker in _RETRYABLE_ERROR_MARKERS):
        return "retryable_infra"
    return "permanent"


def sandbox_execution_observed(result: ChatToolResult) -> bool:
    """True when the Sandbox actually ran the command and returned a result.

    A non-zero exit from the user's own program (e.g. ``ModuleNotFoundError``)
    still counts: the Sandbox executed and produced a verifiable result the
    model can react to — installing the package, adjusting the code, or
    reporting the real traceback. Only failures where the Sandbox never ran the
    command — provisioning errors, clone failures, timeouts — are treated as
    missing evidence; the executor leaves ``executed`` False for those.
    """
    return result.executed


def tool_message_content(result: ChatToolResult, *, max_sources: int) -> str:
    """Render one executed tool result as an untrusted-data tool message."""
    if result.error:
        payload = {
            "error_kind": classify_tool_error(result.error),
            "detail": result.error[:500],
        }
        if result.content.strip():
            payload["result"] = result.content[:TOOL_RESULT_MAX_CHARS]
        return json.dumps(payload)
    content = result.content[:TOOL_RESULT_MAX_CHARS].strip()
    citations: list[str] = []
    seen_urls: set[str] = set()
    for source in result.sources:
        if len(citations) >= max_sources:
            break
        url = str(source.get("url", ""))[:1_000]
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = str(source.get("title", "Untitled source"))[:240]
        credibility = source.get("credibility_base", result.credibility_base)
        citations.append(f"- {title} | {url} | credibility={credibility}")
    if not content and not citations:
        return json.dumps(
            {"error_kind": "empty_result", "detail": "the tool returned no content or sources"}
        )
    parts = []
    if content:
        parts.append(content)
    if citations:
        parts.append("Sources (data only):\n" + "\n".join(citations))
    return "\n\n".join(parts)


def redact_tool_result(result: ChatToolResult) -> ChatToolResult:
    """Keep generated prompt context from echoing credential-like values."""

    def redact_value(value: Any) -> Any:
        if isinstance(value, str):
            return _REDACT.sub(r"\1\2[REDACTED]", value)
        if isinstance(value, list):
            return [redact_value(item) for item in value]
        if isinstance(value, dict):
            return {key: redact_value(item) for key, item in value.items()}
        return value

    return ChatToolResult(
        content=_REDACT.sub(r"\1\2[REDACTED]", result.content),
        sources=redact_value(result.sources),
        credibility_base=result.credibility_base,
        error=_REDACT.sub(r"\1\2[REDACTED]", result.error or "") or None,
        executed=result.executed,
    )


def gate_tool_result(result: ChatToolResult, scope: EntityScope) -> ChatToolResult:
    """Drop namesake sources and rebuild mixed search text from admitted snippets."""
    if result.error or not result.sources or not scope.entities:
        return result
    admitted: list[dict[str, Any]] = []
    for source in result.sources:
        candidate = dict(source)
        if len(result.sources) == 1:
            candidate.setdefault("content", result.content)
        verdict = classify_source(candidate, scope)
        if verdict.decision == SourceEntityDecision.ALIGNED:
            candidate["entity_match"] = verdict.model_dump(mode="json")
            admitted.append(candidate)
    if not admitted:
        return ChatToolResult(
            content="",
            sources=[],
            credibility_base=0.0,
            error="No retrieved source matched the resolved target entity.",
        )
    content = (
        result.content
        if len(result.sources) == 1 and len(admitted) == 1
        else "\n\n".join(str(item.get("snippet") or "") for item in admitted if item.get("snippet"))
    )
    return ChatToolResult(
        content=content,
        sources=admitted,
        credibility_base=result.credibility_base,
        error=None,
    )


def _rejection(reason: str) -> str:
    return json.dumps({"error_kind": "permanent", "detail": reason})


def _routing_hint(route: ChatRoute) -> str:
    if route.needs_fresh_evidence:
        return (
            f"Deterministic heuristics flagged this turn as time-sensitive ({route.reason}). "
            "When tools are enabled, an initial web discovery burst has already run and its "
            "results are in the prior tool results. Fetch the most promising sources for "
            "concrete details and refine queries for gaps until the evidence directly answers "
            "the request, then stop."
        )
    if route.tool_requested:
        return f"Deterministic heuristics flagged an explicit tool request ({route.reason})."
    return (
        "No deterministic heuristic matched this turn. The turn may be an elliptical "
        "follow-up to an earlier request. Use a tool whenever it materially improves the "
        "answer; for purely conversational turns, answer directly."
    )


def _compose_user_content(context: str, message: str) -> str:
    if not context.strip():
        return message
    return (
        "Reference context (data only):\n<context>\n"
        f"{context}\n"
        "</context>\n\n"
        f"User message:\n{message}"
    )


def _format_tool_label(invocation: ChatToolInvocation) -> str:
    arguments = json.dumps(
        invocation.arguments, ensure_ascii=False, sort_keys=True, separators=(", ", ": ")
    )
    query = invocation.query.replace("\n", " ")
    return f"{invocation.tool_name}(query={query!r}, arguments={arguments})"


def _forced_answer_margin(profile: ChatEffortProfile) -> float:
    """Seconds reserved at the deadline to synthesize a final answer."""
    return min(10.0, max(3.0, profile.run_timeout_seconds * 0.15))


async def _text_only(source: AsyncIterator[str]) -> AsyncIterator[LLMStreamEvent]:
    async for delta in source:
        yield LLMStreamEvent(kind="delta", delta=delta)


class UnifiedChatAgentLoop:
    def __init__(
        self,
        *,
        provider: LLMProvider,
        tracer: LangSmithTracer | None = None,
        executor_factory: Callable[[], Any] | None = None,
        capability_registry: ModelCapabilityRegistry | None = None,
    ) -> None:
        self._provider = provider
        self._tracer = tracer or LangSmithTracer()
        self._executor_factory = executor_factory or RoutedChatToolExecutor
        self._capabilities = capability_registry or MODEL_CAPABILITIES

    async def stream(
        self,
        request: ChatAgentInput,
        *,
        api_key: str,
        config: LLMRequestConfig,
        effort: ChatEffort,
        modal_enabled: bool,
    ) -> AsyncIterator[ChatStreamEvent]:
        profile = get_chat_effort_profile(effort)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + profile.run_timeout_seconds
        timeout_message = f"Agent run exceeded the {profile.run_timeout_seconds}-second {effort} cap"
        route = route_chat_request(request.message, context=request.context)
        capability = select_capability(f"{request.context}\n{request.message}")
        trusted_tools_enabled = trusted_function_enabled(modal_enabled)
        sandbox_tools_enabled = sandbox_enabled(modal_enabled)
        entity_scope = lightweight_chat_scope(route.tool_query, context=request.context)

        # A required Sandbox that cannot run (tools off) degrades gracefully:
        # the model tells the user it could not run it, hands back the code, and
        # points to resources — never a hard error in chat.
        if capability.kind == "sandbox" and capability.required and not sandbox_tools_enabled:
            capabilities = await self._capabilities.resolve(
                provider_name=config.provider,
                provider=self._provider,
                api_key=api_key,
                model_id=config.model_id,
            )
            async for event in self._stream_degraded_answer(
                api_key=api_key,
                config=config,
                model=capabilities.as_model(),
                request=request,
                route=route,
                deadline=deadline,
                timeout_message=timeout_message,
                requested_output=config.max_output_tokens,
                started_emitted=False,
            ):
                yield event
            return
        if route.reason == "explicit_tool_request" and not (trusted_tools_enabled or sandbox_tools_enabled):
            raise ToolEvidenceUnavailable("This request requires a tool, but Modal tools are disabled")

        if route.tool_requested and not entity_scope.resolved:
            yield ChatStreamEvent(type="started", model_id=config.model_id)
            yield ChatStreamEvent(
                type="completed",
                model_id=config.model_id,
                content=clarification_for_scope(entity_scope),
            )
            return

        run_id = str(uuid4())
        executor = self._executor_factory() if trusted_tools_enabled or sandbox_tools_enabled else None
        tools_enabled = executor is not None
        capability_task = asyncio.create_task(self._capabilities.resolve(
            provider_name=config.provider,
            provider=self._provider,
            api_key=api_key,
            model_id=config.model_id,
        ))
        seed_task = (
            asyncio.create_task(self._run_seed(executor, route.tool_query, effort, profile, run_id, entity_scope))
            if trusted_tools_enabled and route.needs_fresh_evidence
            else None
        )
        try:
            if tools_enabled:
                yield ChatStreamEvent(
                    type="progress",
                    model_id=config.model_id,
                    progress_kind="routing",
                    message=(
                        f"retrieval expected ({route.reason})"
                        if route.tool_requested
                        else "no heuristic match; model decides whether tools help"
                    ),
                )
                yield ChatStreamEvent(
                    type="progress",
                    model_id=config.model_id,
                    progress_kind="agent_budget",
                    message=(
                        f"up to {profile.max_agent_tool_steps} model turns; "
                        f"action cap={profile.max_tool_actions}; "
                        f"parallel cap={profile.max_parallel_actions}"
                    ),
                )

            async with self._tracer.span(
                "model_lookup",
                run_type="llm",
                metadata={"model_id": config.model_id},
                tags=["chat"],
            ) as span:
                capabilities = await capability_task
                span.end({
                    "context_window": capabilities.context_window,
                    "max_completion_tokens": capabilities.max_completion_tokens,
                })
            model = capabilities.as_model()

            state = _LoopState(
                loaded_skills=set(capability.skill_ids),
                approved_repository_url=capability.repository_url,
                gpu_authorized="GPU" in capability.reason,
            )
            disclosure = route.needs_fresh_evidence and not tools_enabled
            base_system = self._base_system_content(
                route,
                tools_enabled,
                disclosure,
                preloaded_skill_ids=capability.skill_ids,
                sandbox_required=capability.kind == "sandbox" and capability.required,
            )
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": base_system},
                {"role": "user", "content": _compose_user_content(request.context, route.answer_message)},
            ]

            if seed_task is not None:
                async for event in self._merge_seed_results(
                    await seed_task, messages, state, profile, config.model_id
                ):
                    yield event

            requested_output = config.max_output_tokens
            margin = _forced_answer_margin(profile)
            started_emitted = False
            answered = False
            force_answer = False
            max_turns = profile.max_agent_tool_steps if tools_enabled else 1

            for turn_index in range(max_turns):
                remaining = deadline - loop.time()
                if tools_enabled and remaining <= margin:
                    force_answer = True
                    break
                if tools_enabled:
                    messages[0] = {
                        "role": "system",
                        "content": base_system + "\n\n" + self._budget_note(
                            state, profile, turn_index, remaining
                        ),
                    }
                schemas: list[dict[str, Any]] | None = None
                bindings: dict[str, tuple[str, str]] = {}
                if tools_enabled:
                    allowed_kinds = tuple(
                        kind
                        for kind, enabled in (
                            ("trusted_function", trusted_tools_enabled),
                            ("sandbox", sandbox_tools_enabled),
                        )
                        if enabled
                    )
                    disclosed_skills = tuple(sorted(set(NO_LOAD_SKILL_IDS) | state.loaded_skills))
                    planner_schemas, bindings = chat_planner_tool_schemas(
                        allowed_execution_kinds=allowed_kinds,
                        skill_ids=disclosed_skills,
                    )
                    schemas = [*planner_schemas, load_skill_schema()]
                fitted = budget_agent_messages(
                    messages=messages,
                    model=model,
                    requested_output_tokens=requested_output,
                )
                messages = list(fitted.messages)
                if not started_emitted:
                    yield ChatStreamEvent(
                        type="started",
                        model_id=config.model_id,
                        input_token_upper_bound=fitted.input_token_upper_bound,
                        max_output_tokens=fitted.max_output_tokens,
                        context_truncated=fitted.compacted,
                    )
                    started_emitted = True
                if tools_enabled:
                    yield ChatStreamEvent(
                        type="progress",
                        model_id=config.model_id,
                        progress_kind="tool_planning_start",
                        message="Model turn: planning tools or answering",
                    )

                turn_config = replace(config, max_output_tokens=fitted.max_output_tokens)
                result: _TurnResult | None = None
                async for item in self._stream_model_turn(
                    api_key=api_key,
                    config=turn_config,
                    messages=messages,
                    schemas=schemas,
                    deadline=deadline,
                    timeout_message=timeout_message,
                ):
                    if isinstance(item, _TurnResult):
                        result = item
                    else:
                        yield item
                assert result is not None
                if result.text:
                    if (
                        capability.kind == "sandbox"
                        and capability.required
                        and not state.sandbox_evidence_succeeded
                    ):
                        # The Sandbox never produced usable evidence. Discard the
                        # model's unsupported answer and degrade gracefully: tell
                        # the user it could not run, return the code, and point to
                        # resources.
                        if executor is not None:
                            try:
                                await executor.aclose()
                            except Exception:
                                pass
                            executor = None
                        async for event in self._stream_degraded_answer(
                            api_key=api_key,
                            config=config,
                            model=model,
                            request=request,
                            route=route,
                            deadline=deadline,
                            timeout_message=timeout_message,
                            requested_output=requested_output,
                            started_emitted=started_emitted,
                        ):
                            yield event
                        answered = True
                        break
                    if state.sandbox_evidence_succeeded and executor is not None:
                        try:
                            await executor.aclose()
                        except Exception:
                            pass
                        executor = None
                        yield ChatStreamEvent(
                            type="progress",
                            model_id=config.model_id,
                            progress_kind="sandbox_closed",
                            message="Task-scoped Sandbox workspace closed",
                        )
                    yield ChatStreamEvent(type="completed", model_id=config.model_id, content=result.text)
                    answered = True
                    break
                if not result.tool_calls:
                    raise GroqProviderError(
                        code="provider_empty_stream",
                        message=(
                            f"{config.provider.title()} model {config.model_id} completed the "
                            "stream without visible assistant content"
                        ),
                        retryable=True,
                    )

                cancelled = False
                async for event in self._run_batch_with_progress(
                    executor=executor,
                    calls=result.tool_calls,
                    bindings=bindings,
                    run_id=run_id,
                    effort=effort,
                    profile=profile,
                    state=state,
                    messages=messages,
                    config=config,
                    deadline=deadline,
                    margin=margin,
                    entity_scope=entity_scope,
                ):
                    if event is None:
                        cancelled = True
                    else:
                        yield event
                if cancelled:
                    force_answer = True
                    break

            if not answered:
                if not force_answer and not tools_enabled:
                    # The single text-only turn produced nothing; the empty-stream
                    # branch above already raised, so this is unreachable, but the
                    # invariant is stated for clarity.
                    raise AssertionError("text-only turn ended without answer or error")
                remaining = deadline - loop.time()
                if remaining <= 1.0:
                    raise ChatRuntimeLimitExceeded(timeout_message)
                if (
                    capability.kind == "sandbox"
                    and capability.required
                    and not state.sandbox_evidence_succeeded
                ):
                    # Budget ended before the Sandbox produced usable evidence.
                    # Degrade gracefully instead of erroring: return the code and
                    # resources so the user can run it themselves.
                    if executor is not None:
                        try:
                            await executor.aclose()
                        except Exception:
                            pass
                        executor = None
                    async for event in self._stream_degraded_answer(
                        api_key=api_key,
                        config=config,
                        model=model,
                        request=request,
                        route=route,
                        deadline=deadline,
                        timeout_message=timeout_message,
                        requested_output=requested_output,
                        started_emitted=started_emitted,
                    ):
                        yield event
                    return
                yield ChatStreamEvent(
                    type="progress",
                    model_id=config.model_id,
                    progress_kind="routing",
                    message="budget reached; answering from gathered evidence",
                )
                messages[0] = {"role": "system", "content": base_system}
                messages.append({"role": "system", "content": _FORCED_ANSWER_NOTE})
                fitted = budget_agent_messages(
                    messages=messages,
                    model=model,
                    requested_output_tokens=requested_output,
                )
                if not started_emitted:
                    yield ChatStreamEvent(
                        type="started",
                        model_id=config.model_id,
                        input_token_upper_bound=fitted.input_token_upper_bound,
                        max_output_tokens=fitted.max_output_tokens,
                        context_truncated=fitted.compacted,
                    )
                result = None
                async for item in self._stream_model_turn(
                    api_key=api_key,
                    config=replace(config, max_output_tokens=fitted.max_output_tokens),
                    messages=list(fitted.messages),
                    schemas=None,
                    deadline=deadline,
                    timeout_message=timeout_message,
                ):
                    if isinstance(item, _TurnResult):
                        result = item
                    else:
                        yield item
                assert result is not None
                if not result.text:
                    raise GroqProviderError(
                        code="provider_empty_stream",
                        message=(
                            f"{config.provider.title()} model {config.model_id} completed the "
                            "stream without visible assistant content"
                        ),
                        retryable=True,
                    )
                if state.sandbox_evidence_succeeded and executor is not None:
                    try:
                        await executor.aclose()
                    except Exception:
                        pass
                    executor = None
                    yield ChatStreamEvent(
                        type="progress",
                        model_id=config.model_id,
                        progress_kind="sandbox_closed",
                        message="Task-scoped Sandbox workspace closed",
                    )
                yield ChatStreamEvent(type="completed", model_id=config.model_id, content=result.text)
        except BaseException:
            for task in (capability_task, seed_task):
                if task is not None and not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
            raise
        finally:
            if executor is not None:
                close = getattr(executor, "aclose", None)
                if close is not None:
                    await close()

    def _base_system_content(
        self,
        route: ChatRoute,
        tools_enabled: bool,
        disclosure: bool,
        *,
        preloaded_skill_ids: tuple[str, ...] = (),
        sandbox_required: bool = False,
    ) -> str:
        parts = [build_runtime_system_prompt(tool_mode="agent" if tools_enabled else "direct")]
        if tools_enabled:
            parts.append(skill_catalog_text())
            if preloaded_skill_ids:
                parts.extend(load_skill_instructions(skill_id) for skill_id in preloaded_skill_ids)
            parts.append(
                "Repository-specific claims require evidence from a Modal Sandbox that inspected "
                "the repository. Web results may supplement that evidence but never replace it. "
                "Never execute arbitrary code in the trusted Function container and never fall "
                "back across that isolation boundary."
            )
            if sandbox_required:
                parts.append(
                    "This turn requires Sandbox evidence. Do not answer repository, code, or data "
                    "claims until a Sandbox tool succeeds; if it fails, report that verification "
                    "failed instead of substituting web-only claims."
                )
        parts.append(f"Routing assessment: {_routing_hint(route)}")
        if disclosure:
            parts.append(
                "Live retrieval is unavailable for this turn. Answer from your own knowledge "
                "and state explicitly that live data could not be retrieved and details may "
                "be outdated."
            )
        return "\n\n".join(parts)

    def _budget_note(
        self,
        state: _LoopState,
        profile: ChatEffortProfile,
        turns_used: int,
        remaining_seconds: float,
    ) -> str:
        return (
            f"Budget remaining: {profile.max_agent_tool_steps - turns_used} model turns, "
            f"{max(0, profile.max_tool_actions - state.total_actions)} tool actions, "
            f"~{int(remaining_seconds)}s. Stop and answer as soon as the evidence is sufficient."
        )

    async def _stream_degraded_answer(
        self,
        *,
        api_key: str,
        config: LLMRequestConfig,
        model: Any,
        request: ChatAgentInput,
        route: ChatRoute,
        deadline: float,
        timeout_message: str,
        requested_output: int,
        started_emitted: bool,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Answer gracefully when the Sandbox could not run the request.

        Rather than surfacing a hard ``tool_evidence_unavailable`` error in
        chat, run one text-only model turn seeded with the degradation note so
        the model tells the user it could not run it, hands back the code to
        copy, and points to resources. No tool schemas are offered: this turn
        cannot execute anything.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._base_system_content(route, False, False)},
            {"role": "system", "content": _SANDBOX_DEGRADED_NOTE},
            {"role": "user", "content": _compose_user_content(request.context, route.answer_message)},
        ]
        fitted = budget_agent_messages(
            messages=messages,
            model=model,
            requested_output_tokens=requested_output,
        )
        if not started_emitted:
            yield ChatStreamEvent(
                type="started",
                model_id=config.model_id,
                input_token_upper_bound=fitted.input_token_upper_bound,
                max_output_tokens=fitted.max_output_tokens,
                context_truncated=fitted.compacted,
            )
        yield ChatStreamEvent(
            type="progress",
            model_id=config.model_id,
            progress_kind="routing",
            message="Sandbox unavailable; returning the code and guidance instead",
        )
        result: _TurnResult | None = None
        async for item in self._stream_model_turn(
            api_key=api_key,
            config=replace(config, max_output_tokens=fitted.max_output_tokens),
            messages=list(fitted.messages),
            schemas=None,
            deadline=deadline,
            timeout_message=timeout_message,
        ):
            if isinstance(item, _TurnResult):
                result = item
            else:
                yield item
        assert result is not None
        if not result.text:
            raise GroqProviderError(
                code="provider_empty_stream",
                message=(
                    f"{config.provider.title()} model {config.model_id} completed the "
                    "stream without visible assistant content"
                ),
                retryable=True,
            )
        yield ChatStreamEvent(type="completed", model_id=config.model_id, content=result.text)

    async def _run_seed(
        self,
        executor: Any,
        query: str,
        effort: ChatEffort,
        profile: ChatEffortProfile,
        run_id: str,
        entity_scope: EntityScope,
    ) -> list[tuple[str, str, dict[str, Any], ChatToolResult]]:
        """Run one speculative discovery call concurrently with turn setup.

        Failures are absorbed: they arrive as typed error tool messages the
        model can react to, never as a failed turn.
        """

        async def one(call_id: str, seed_query: str, arguments: dict[str, Any]):
            invocation = ChatToolInvocation(
                run_id=run_id,
                skill_id=_SEED_SKILL_ID,
                tool_name="web_search",
                query=seed_query,
                arguments=arguments,
                effort=effort,
                timeout_seconds=profile.timeout_seconds,
            )
            validate_chat_tool_invocation(invocation)
            try:
                async with asyncio.timeout(profile.timeout_seconds):
                    result = await executor.execute(invocation)
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
            return call_id, seed_query, arguments, redact_tool_result(result)

        scoped_query = scope_search_query(query, entity_scope)
        result = await one("seed_0", scoped_query, {"max_results": 8})
        call_id, seed_query, arguments, tool_result = result
        return [(call_id, seed_query, arguments, gate_tool_result(tool_result, entity_scope))]

    async def _merge_seed_results(
        self,
        seeds: list[tuple[str, str, dict[str, Any], ChatToolResult]],
        messages: list[dict[str, Any]],
        state: _LoopState,
        profile: ChatEffortProfile,
        model_id: str,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Fold seed results in as ordinary prior tool calls the model made."""
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": _SEED_FUNCTION_NAME,
                        "arguments": json.dumps({"query": seed_query, "arguments": arguments}),
                    },
                }
                for call_id, seed_query, arguments, _result in seeds
            ],
        })
        for call_id, seed_query, arguments, result in seeds:
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": tool_message_content(result, max_sources=profile.max_document_chunks),
            })
            state.calls_by_tool["web_search"] = state.calls_by_tool.get("web_search", 0) + 1
            state.total_actions += 1
            rendered_arguments = json.dumps(
                arguments, ensure_ascii=False, sort_keys=True, separators=(", ", ": ")
            )
            label = f"web_search(query={seed_query!r}, arguments={rendered_arguments})"
            yield ChatStreamEvent(
                type="progress",
                model_id=model_id,
                progress_kind="tool_failed" if result.error else "tool_completed",
                message=label if result.error else f"{label} — {len(result.sources)} source(s)",
            )

    async def _stream_model_turn(
        self,
        *,
        api_key: str,
        config: LLMRequestConfig,
        messages: list[dict[str, Any]],
        schemas: list[dict[str, Any]] | None,
        deadline: float,
        timeout_message: str,
    ) -> AsyncIterator[ChatStreamEvent | _TurnResult]:
        """Run one model turn, yielding answer deltas and a terminal _TurnResult.

        The turn commits to its first modality: text deltas mean this is the
        answer (later tool calls in the same turn are ignored); tool calls mean
        content in the same turn is planner chatter and is dropped.
        """
        loop = asyncio.get_running_loop()
        stream_retry = RetryPolicy(max_retries=2, base_delay_seconds=0.5, max_delay_seconds=4.0)
        attempt = 0
        low_effort_retried = False
        turn_config = config
        while True:
            text = ""
            calls: tuple[LLMToolCall, ...] = ()
            failure: GroqProviderError | None = None
            async with self._tracer.span(
                "model_turn",
                run_type="llm",
                metadata={
                    "model_id": turn_config.model_id,
                    "with_tools": schemas is not None,
                    "attempt": attempt,
                },
                tags=["chat", "model-turn"],
            ) as span:
                source = (
                    self._provider.stream_with_tools(
                        api_key=api_key,
                        config=turn_config,
                        messages=list(messages),
                        tools=schemas,
                    )
                    if schemas is not None
                    else _text_only(self._provider.stream_chat(
                        api_key=api_key,
                        config=turn_config,
                        messages=list(messages),
                    ))
                )
                iterator = source.__aiter__()
                try:
                    while True:
                        remaining = deadline - loop.time()
                        if remaining <= 0:
                            raise ChatRuntimeLimitExceeded(timeout_message)
                        try:
                            event = await asyncio.wait_for(anext(iterator), timeout=remaining)
                        except StopAsyncIteration:
                            break
                        except TimeoutError as exc:
                            raise ChatRuntimeLimitExceeded(timeout_message) from exc
                        if event.kind == "delta" and event.delta and not calls:
                            text += event.delta
                            yield ChatStreamEvent(
                                type="delta", model_id=config.model_id, delta=event.delta
                            )
                        elif event.kind == "tool_calls" and not text:
                            calls = event.tool_calls
                except GroqProviderError as exc:
                    # Retries are only safe before the first visible output.
                    if text or calls or not exc.retryable or attempt >= stream_retry.max_retries:
                        raise
                    failure = exc
                span.end({
                    "delta_characters": len(text),
                    "tool_call_count": len(calls),
                    "retrying": failure is not None,
                })
            if failure is not None:
                attempt += 1
                try:
                    delay = (
                        float(failure.retry_after_seconds)
                        if failure.retry_after_seconds
                        else stream_retry.delay(attempt - 1)
                    )
                except (TypeError, ValueError):
                    delay = stream_retry.delay(attempt - 1)
                await asyncio.sleep(min(8.0, max(0.0, delay)))
                continue
            if not text and not calls and turn_config.reasoning_effort not in {None, "low"} and not low_effort_retried:
                # Reasoning tokens and visible text share the completion budget;
                # a reasoning model can finish without visible output. Retry
                # only that empty case, once, at low effort.
                low_effort_retried = True
                turn_config = replace(turn_config, reasoning_effort="low")
                continue
            yield _TurnResult(text=text, tool_calls=calls)
            return

    async def _run_batch_with_progress(
        self,
        *,
        executor: Any,
        calls: tuple[LLMToolCall, ...],
        bindings: dict[str, tuple[str, str]],
        run_id: str,
        effort: ChatEffort,
        profile: ChatEffortProfile,
        state: _LoopState,
        messages: list[dict[str, Any]],
        config: LLMRequestConfig,
        deadline: float,
        margin: float,
        entity_scope: EntityScope,
    ) -> AsyncIterator[ChatStreamEvent | None]:
        """Execute one tool batch, forwarding live progress events.

        Yields ``None`` (once, terminally) when the deadline margin was hit and
        the batch was cancelled: message structure stays protocol-valid because
        the batch appends its assistant/tool messages atomically at the end.
        """
        loop = asyncio.get_running_loop()
        progress_queue: asyncio.Queue[ChatStreamEvent] = asyncio.Queue()

        async def emit(
            kind: str,
            message: str,
            elapsed: float | None = None,
            **details: Any,
        ) -> None:
            await progress_queue.put(ChatStreamEvent(
                type="progress",
                model_id=config.model_id,
                progress_kind=kind,
                message=message,
                elapsed_seconds=elapsed,
                profile=details.get("profile"),
                safe_command_label=details.get("safe_command_label"),
                exit_code=details.get("exit_code"),
                truncated=details.get("truncated"),
            ))

        batch_task = asyncio.create_task(self._execute_batch(
            executor=executor,
            calls=calls,
            bindings=bindings,
            run_id=run_id,
            effort=effort,
            profile=profile,
            state=state,
            messages=messages,
            emit=emit,
            entity_scope=entity_scope,
        ))
        try:
            while not batch_task.done() or not progress_queue.empty():
                remaining = deadline - margin - loop.time()
                if remaining <= 0:
                    batch_task.cancel()
                    await asyncio.gather(batch_task, return_exceptions=True)
                    yield None
                    return
                try:
                    yield await asyncio.wait_for(progress_queue.get(), timeout=min(0.05, remaining))
                except TimeoutError:
                    continue
            await batch_task
        except BaseException:
            if not batch_task.done():
                batch_task.cancel()
                await asyncio.gather(batch_task, return_exceptions=True)
            raise

    async def _execute_batch(
        self,
        *,
        executor: Any,
        calls: tuple[LLMToolCall, ...],
        bindings: dict[str, tuple[str, str]],
        run_id: str,
        effort: ChatEffort,
        profile: ChatEffortProfile,
        state: _LoopState,
        messages: list[dict[str, Any]],
        emit: Callable[..., Any],
        entity_scope: EntityScope,
    ) -> None:
        immediate: dict[str, str] = {}
        pending: list[tuple[LLMToolCall, ChatToolInvocation]] = []
        for call in calls:
            invocation, content = self._plan_call(call, bindings, run_id, effort, profile, state)
            if invocation is not None:
                if invocation.tool_name in _ENTITY_RETRIEVAL_TOOLS and not entity_scope.resolved:
                    immediate[call.id] = _rejection(
                        "Target entity is ambiguous. Do not search; ask the user for one identifying detail."
                    )
                else:
                    pending.append((call, invocation))
            else:
                immediate[call.id] = content or _rejection("call produced no result")

        semaphore = asyncio.Semaphore(profile.max_parallel_actions)
        sandbox_semaphore = asyncio.Semaphore(profile.max_sandbox_workers)

        async def execute_one(call: LLMToolCall, invocation: ChatToolInvocation) -> tuple[str, str]:
            async with semaphore:
                if invocation.tool_name in _ENTITY_RETRIEVAL_TOOLS:
                    invocation = invocation.model_copy(
                        update={"query": scope_search_query(invocation.query, entity_scope)}
                    )
                started_at = asyncio.get_running_loop().time()
                is_sandbox = TOOL_REGISTRY.descriptor(invocation.tool_name).execution_kind == "sandbox"
                label = _format_sandbox_label(invocation) if is_sandbox else _format_tool_label(invocation)
                await emit(
                    _sandbox_progress_kind(invocation.tool_name, started=True) if is_sandbox else "tool_start",
                    label,
                    None,
                    **(_sandbox_progress_details(invocation, None, label) if is_sandbox else {}),
                )
                try:
                    async with self._tracer.span(
                        f"modal_tool:{invocation.skill_id}/{invocation.tool_name}",
                        run_type="tool",
                        inputs={"query": self._tracer.text(invocation.query)},
                        metadata={
                            "skill_id": invocation.skill_id,
                            "tool_name": invocation.tool_name,
                            "effort": str(effort),
                        },
                        tags=["chat", "modal", "tool"],
                    ) as span:
                        async with asyncio.timeout(profile.timeout_seconds):
                            if is_sandbox:
                                async with sandbox_semaphore:
                                    result = await executor.execute(invocation)
                            else:
                                result = await executor.execute(invocation)
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
                if (
                    is_sandbox
                    and invocation.tool_name in {
                        "repository_inspection", "dataset_analysis", "code_execution",
                        "sandbox_exec", "sandbox_list", "sandbox_read",
                    }
                    and (result.error is None or sandbox_execution_observed(result))
                ):
                    state.sandbox_evidence_succeeded = True
                await emit(
                    (
                        "sandbox_failed"
                        if is_sandbox and result.error
                        else _sandbox_progress_kind(invocation.tool_name, started=False)
                        if is_sandbox
                        else "tool_failed" if result.error else "tool_completed"
                    ),
                    label if result.error else f"{label} — {len(result.sources)} source(s)",
                    elapsed,
                    **(_sandbox_progress_details(invocation, result, label) if is_sandbox else {}),
                )
                gated = (
                    gate_tool_result(result, entity_scope)
                    if invocation.tool_name in _ENTITY_RETRIEVAL_TOOLS
                    else result
                )
                return call.id, tool_message_content(
                    redact_tool_result(gated), max_sources=profile.max_document_chunks
                )

        results = dict(await asyncio.gather(
            *(execute_one(call, invocation) for call, invocation in pending)
        ))

        # Appended atomically after execution so a cancelled batch never leaves
        # an assistant tool_calls message without its tool replies.
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.raw_arguments or "{}"},
                }
                for call in calls
            ],
        })
        for call in calls:
            content = immediate.get(call.id) or results.get(call.id) or _rejection("call produced no result")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})

    def _plan_call(
        self,
        call: LLMToolCall,
        bindings: dict[str, tuple[str, str]],
        run_id: str,
        effort: ChatEffort,
        profile: ChatEffortProfile,
        state: _LoopState,
    ) -> tuple[ChatToolInvocation | None, str | None]:
        """Validate one model tool call against caps and contracts.

        Returns either an executable invocation or the immediate tool-message
        content (skill instructions or a typed rejection the model can react to).
        """
        if call.name == LOAD_SKILL_TOOL_NAME:
            skill_id = (call.arguments or {}).get("skill_id")
            if not isinstance(skill_id, str) or not skill_id:
                return None, _rejection("load_skill requires a skill_id string")
            if skill_id in state.loaded_skills:
                return None, f"Skill {skill_id} instructions are already loaded above."
            try:
                instructions = load_skill_instructions(skill_id)
            except KeyError:
                return None, _rejection(
                    f"unknown skill {skill_id!r}; valid skills: {', '.join(chat_skill_ids())}"
                )
            state.loaded_skills.add(skill_id)
            return None, instructions
        if call.arguments is None:
            return None, _rejection("tool arguments were not valid JSON")
        binding = bindings.get(call.name)
        if binding is None:
            return None, _rejection(f"unknown tool {call.name!r}")
        skill_id, tool_name = binding
        raw_query = call.arguments.get("query")
        raw_arguments = call.arguments.get("arguments")
        if not isinstance(raw_query, str) or not raw_query.strip() or not isinstance(raw_arguments, dict):
            return None, _rejection('expected arguments {"query": str, "arguments": object}')
        if state.total_actions >= profile.max_tool_actions:
            return None, _rejection("tool action budget exhausted; answer from the evidence above")
        per_tool_cap = (
            profile.max_code_repair_cycles + 1
            if tool_name == "code_execution"
            else profile.max_calls_per_tool_type
        )
        if state.calls_by_tool.get(tool_name, 0) >= per_tool_cap:
            return None, _rejection(f"per-tool cap reached for {tool_name}")
        arguments = dict(raw_arguments)
        if tool_name in {"repository_inspection", "sandbox_create"}:
            proposed_repository = arguments.get("repository_url")
            if (
                proposed_repository
                and validated_repository_url(str(proposed_repository)) != state.approved_repository_url
            ):
                return None, _rejection(
                    "repository_url was not validated from the user request; never invent repository URLs"
                )
            if proposed_repository and state.approved_repository_url:
                arguments["repository_url"] = state.approved_repository_url
        if (
            tool_name == "sandbox_create"
            and arguments.get("profile") == "gpu"
            and not state.gpu_authorized
        ):
            return None, _rejection("GPU profile requires an explicit GPU workload request")
        # One DDGS attempt per agent run; later general-web discovery goes to
        # Tavily, including calls in the same parallel burst.
        if tool_name == "web_search" and state.calls_by_tool.get(tool_name, 0) > 0:
            arguments["search_backend"] = "tavily"
        try:
            invocation = ChatToolInvocation(
                run_id=run_id,
                skill_id=skill_id,
                tool_name=tool_name,
                query=raw_query,
                arguments=arguments,
                effort=effort,
                timeout_seconds=profile.timeout_seconds,
            )
            validate_chat_tool_invocation(invocation)
        except (ValueError, KeyError) as exc:
            return None, _rejection(f"invalid tool call: {exc}")
        state.calls_by_tool[tool_name] = state.calls_by_tool.get(tool_name, 0) + 1
        state.total_actions += 1
        return invocation, None


def _sandbox_progress_kind(tool_name: str, *, started: bool) -> str:
    if tool_name == "sandbox_create":
        return "sandbox_created" if started else "sandbox_ready"
    if tool_name == "sandbox_close":
        return "sandbox_command_started" if started else "sandbox_closed"
    return "sandbox_command_started" if started else "sandbox_command_completed"


def _format_sandbox_label(invocation: ChatToolInvocation) -> str:
    arguments = invocation.arguments
    if invocation.tool_name == "sandbox_create":
        return f"sandbox_create(profile={arguments.get('profile', 'policy-selected')!r})"
    if invocation.tool_name == "sandbox_exec":
        argv = arguments.get("argv") or []
        command = str(argv[0])[:80] if argv else "command"
        return f"sandbox_exec(command={command!r})"
    if invocation.tool_name == "sandbox_write":
        return f"sandbox_write(file_count={len(arguments.get('files') or {})})"
    if invocation.tool_name == "repository_inspection":
        return "repository_inspection(public GitHub repository)"
    if invocation.tool_name in {"dataset_analysis", "code_execution"}:
        return f"{invocation.tool_name}(isolated workspace)"
    return f"{invocation.tool_name}(task workspace)"


def _sandbox_progress_details(
    invocation: ChatToolInvocation,
    result: ChatToolResult | None,
    label: str,
) -> dict[str, Any]:
    profile = invocation.arguments.get("profile")
    if profile is None:
        profile = {
            "repository_inspection": "repository",
            "dataset_analysis": "data",
            "code_execution": "code",
        }.get(invocation.tool_name)
    details: dict[str, Any] = {
        "profile": str(profile) if profile else None,
        "safe_command_label": label,
    }
    if result is None or not result.content.startswith("{"):
        return details
    try:
        payload = json.loads(result.content)
    except (TypeError, ValueError):
        return details
    if isinstance(payload, dict):
        provenance = payload.get("provenance")
        if isinstance(provenance, dict) and provenance.get("profile"):
            details["profile"] = str(provenance["profile"])
        if isinstance(payload.get("exit_code"), int):
            details["exit_code"] = payload["exit_code"]
        if isinstance(payload.get("truncated"), bool):
            details["truncated"] = payload["truncated"]
    return details
