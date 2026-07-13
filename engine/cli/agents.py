from __future__ import annotations

from collections.abc import AsyncIterator
import asyncio
import os
from typing import Any, Callable, Protocol
from uuid import uuid4

from engine.chat import ChatAgent, ChatAgentInput
from engine.chat.effort import chat_output_budget, get_chat_effort_profile, reasoning_effort_for_model
from engine.chat.freshness import requests_tool_use, requires_fresh_evidence
from engine.chat.groq_planner import GroqChatToolPlanner
from engine.chat.modal_tools import ModalToolExecutor
from engine.chat.tool_loop import BoundedChatToolLoop, ExecutedToolCall, PlannedToolCall
from engine.cli.context import ChatContextSelector, LocalSummaryGenerator
from engine.cli.models import TerminalHistoryTurn, TerminalOutput, TerminalSession
from engine.llm.config import LLMRequestConfig
from engine.llm.providers import LLMProvider, provider_for
from engine.observability import LangSmithTracer


class TerminalAgent(Protocol):
    """Stable adapter boundary for chat now and research agents later."""

    name: str

    async def stream(self, *, message: str, session: TerminalSession) -> AsyncIterator[TerminalOutput]: ...


class FreshnessEvidenceUnavailable(ValueError):
    """A current-facts request could not obtain the required live evidence."""


class _FreshnessWebSearchPlanner:
    """Avoid an expensive model planning call for clearly fresh requests."""

    async def plan(self, *, query: str, context: str, prior_results: tuple[ExecutedToolCall, ...]) -> PlannedToolCall | None:
        if prior_results:
            return None
        return PlannedToolCall(
            skill_id="general_web_research",
            tool_name="web_search",
            query=query,
            arguments={"max_results": 8},
        )


class ChatTerminalAgent:
    name = "chat"

    def __init__(
        self,
        *,
        summary_generator: LocalSummaryGenerator | None = None,
        provider: LLMProvider | None = None,
        tracer: LangSmithTracer | None = None,
        tool_executor_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._provider_override = provider
        self._tracer = tracer or LangSmithTracer()
        self._selector = ChatContextSelector()
        self._summary_generator = summary_generator
        self._tool_executor_factory = tool_executor_factory or ModalToolExecutor

    async def stream(self, *, message: str, session: TerminalSession) -> AsyncIterator[TerminalOutput]:
        response = ""
        async with self._tracer.span(
            "chat.turn",
            inputs={"message": self._tracer.text(message)},
            metadata={
                "agent": self.name,
                "model_id": session.model_id,
                "effort": str(session.effort),
                "modal_enabled": os.getenv("SINGULARITY_MODAL_ENABLED", "0") == "1",
                "history_turn_count": len(session.history),
                "loaded_file_count": len(session.context_files),
            },
            tags=["chat", "cli"],
        ) as span:
            try:
                async for output in self._stream_inner(message=message, session=session):
                    if output.kind == "delta":
                        response += output.content
                    yield output
            except BaseException:
                span.end({"status": "failed", "response": self._tracer.text(response)})
                raise
            else:
                span.end({"status": "completed", "response": self._tracer.text(response)})

    async def _stream_inner(self, *, message: str, session: TerminalSession) -> AsyncIterator[TerminalOutput]:
        profile = get_chat_effort_profile(session.effort)
        async with self._tracer.span(
            "local_context_selection",
            inputs={"query": self._tracer.text(message)},
            metadata={"effort": str(session.effort), "loaded_file_count": len(session.context_files)},
            tags=["chat", "context"],
        ) as span:
            selection = self._selector.select(session=session, query=message)
            span.end({
                "recent_turn_count": len(selection.recent_turns),
                "old_turn_count": len(selection.old_turns),
                "document_chunk_count": len(selection.document_chunks),
                "compaction_required": selection.compaction_required,
            })
        config = LLMRequestConfig(
            provider=session.provider,
            credential_id="terminal",
            model_id=session.model_id,
            temperature=session.temperature,
            max_output_tokens=chat_output_budget(session.model_id, session.max_output_tokens),
            reasoning_effort=reasoning_effort_for_model(session.model_id, session.effort),
        )
        provider = self._provider_override or provider_for(session.provider)
        context = selection.context
        needs_fresh_evidence = requires_fresh_evidence(message)
        tool_requested = requests_tool_use(message)
        modal_enabled = os.getenv("SINGULARITY_MODAL_ENABLED", "0") == "1"
        if tool_requested and not modal_enabled:
            raise FreshnessEvidenceUnavailable("This request requires a tool, but Modal tools are disabled")
        if modal_enabled and tool_requested:
            planner = (
                _FreshnessWebSearchPlanner()
                if needs_fresh_evidence
                else GroqChatToolPlanner(provider=provider, api_key=session.api_key, config=config)
            )
            progress_queue: asyncio.Queue[TerminalOutput] = asyncio.Queue()

            async def emit_progress(kind: str, content: str, elapsed: float | None) -> None:
                await progress_queue.put(TerminalOutput(kind=kind, content=content, elapsed_seconds=elapsed))

            executor = self._tool_executor_factory()
            tool_task = asyncio.create_task(
                BoundedChatToolLoop(
                    planner=planner,
                    executor=executor,
                    tracer=self._tracer,
                ).run(
                    run_id=str(uuid4()),
                    query=message,
                    effort=session.effort,
                    context=context,
                    progress_callback=emit_progress,
                )
            )
            try:
                while not tool_task.done() or not progress_queue.empty():
                    try:
                        progress = await asyncio.wait_for(progress_queue.get(), timeout=0.05)
                    except TimeoutError:
                        continue
                    yield progress
                executed = await tool_task
            except Exception as exc:
                if not tool_task.done():
                    tool_task.cancel()
                    await asyncio.gather(tool_task, return_exceptions=True)
                yield TerminalOutput(kind="metadata", content=f"tool loop unavailable: {type(exc).__name__}")
                if tool_requested:
                    raise FreshnessEvidenceUnavailable(
                        f"Required tool execution failed during {type(exc).__name__}; no unsupported fallback was generated"
                    ) from exc
                executed = ()
            finally:
                close = getattr(executor, "aclose", None)
                if close is not None:
                    await close()
            if executed:
                tool_context = self._tool_context(executed, max_citations=profile.max_document_chunks)
                if tool_requested and not tool_context:
                    raise FreshnessEvidenceUnavailable(
                        "Live web evidence returned no usable sources; no historical fallback was generated"
                    )
                context = "\n\n".join(part for part in (context, tool_context) if part)
            elif tool_requested:
                raise FreshnessEvidenceUnavailable(
                    "Live web evidence returned no usable sources; no historical fallback was generated"
                )

        assistant_content = ""
        session.history.append(TerminalHistoryTurn("user", message))
        yield TerminalOutput(kind="thinking", content="")
        try:
            async with asyncio.timeout(profile.timeout_seconds):
                async for event in ChatAgent(provider=provider, tracer=self._tracer).stream(
                    ChatAgentInput(context=context, message=message),
                    api_key=session.api_key,
                    config=config,
                ):
                    if event.type == "started":
                        truncation = ", context trimmed" if event.context_truncated else ""
                        yield TerminalOutput(
                            kind="model_started",
                            content=(
                                f"effort={session.effort}, model={event.model_id}, input<={event.input_token_upper_bound}, "
                                f"output<={event.max_output_tokens}{truncation}"
                            ),
                        )
                    elif event.type == "delta" and event.delta:
                        assistant_content += event.delta
                        yield TerminalOutput(kind="delta", content=event.delta)
                    elif event.type == "completed" and event.content:
                        assistant_content = event.content
        except TimeoutError as exc:
            raise TimeoutError(
                f"Final answer generation timed out after {profile.timeout_seconds} seconds"
            ) from exc
        yield TerminalOutput(kind="completed", content="")
        if assistant_content:
            session.history.append(TerminalHistoryTurn("assistant", assistant_content))
            if self._selector.select(session=session, query=message).compaction_required:
                if self._summary_generator is None:
                    yield TerminalOutput(kind="metadata", content="local compaction threshold reached; summary skill not registered")
                else:
                    try:
                        async with self._tracer.span(
                            "local_compaction_attempt",
                            metadata={"raw_turn_count": len(session.history) - session.compacted_through},
                            tags=["chat", "compaction"],
                        ) as span:
                            compacted = await self._summary_generator.summarize(
                                previous_summary=session.compacted_summary,
                                turns=tuple(session.history[session.compacted_through :]),
                                max_output_tokens=max(128, int(profile.max_recent_raw_context_tokens * 0.20)),
                            )
                            span.end({"summary_characters": len(compacted)})
                        if not compacted.strip():
                            raise ValueError("summary generator returned empty content")
                    except Exception as exc:
                        yield TerminalOutput(kind="metadata", content=f"local summary retained: {type(exc).__name__}")
                    else:
                        # Only advance the marker after a complete replacement
                        # is available; raw turns remain intact for recovery.
                        session.compacted_summary = compacted
                        session.compacted_through = len(session.history)
                        yield TerminalOutput(kind="metadata", content="local chat history compacted")

    @staticmethod
    def _tool_context(executed, *, max_citations: int) -> str:
        """Compact trusted results into data-only evidence and source references."""
        parts: list[str] = []
        citations: list[str] = []
        for item in executed:
            if item.result.error:
                continue
            parts.append(
                f"Tool result ({item.skill_id}/{item.tool_name}, data only):\n{item.result.content[:8_000]}"
            )
            for source in item.result.sources:
                if len(citations) >= max_citations:
                    break
                title = str(source.get("title", "Untitled source"))[:240]
                url = str(source.get("url", ""))[:1_000]
                credibility = source.get("credibility_base", item.result.credibility_base)
                citations.append(f"- {title} | {url} | credibility={credibility}")
        if citations:
            parts.append("Tool sources (data only):\n" + "\n".join(citations))
        return "\n\n".join(parts)
