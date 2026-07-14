from __future__ import annotations

from collections.abc import AsyncIterator
import os
from typing import Any, Callable, Protocol

from engine.chat import ChatAgentInput
from engine.chat.effort import get_chat_effort_profile, provider_output_budget, reasoning_effort_for_model
from engine.chat.runtime import ChatRuntime, ToolEvidenceUnavailable
from engine.cli.context import ChatContextSelector, LocalSummaryGenerator
from engine.cli.models import TerminalHistoryTurn, TerminalOutput, TerminalSession
from engine.llm.config import LLMRequestConfig
from engine.llm.providers import LLMProvider, provider_for
from engine.observability import LangSmithTracer


class TerminalAgent(Protocol):
    """Stable adapter boundary for chat now and research agents later."""

    name: str

    async def stream(self, *, message: str, session: TerminalSession) -> AsyncIterator[TerminalOutput]: ...


FreshnessEvidenceUnavailable = ToolEvidenceUnavailable


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
        self._tool_executor_factory = tool_executor_factory

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
            max_output_tokens=provider_output_budget(
                session.provider,
                session.model_id,
                session.max_output_tokens,
                model_max_completion_tokens=session.model_max_completion_tokens,
            ),
            reasoning_effort=reasoning_effort_for_model(session.model_id, session.effort),
        )
        provider = self._provider_override or provider_for(session.provider)
        context = selection.context
        modal_enabled = os.getenv("SINGULARITY_MODAL_ENABLED", "0") == "1"

        assistant_content = ""
        session.history.append(TerminalHistoryTurn("user", message))
        yield TerminalOutput(kind="thinking", content="")
        runtime = ChatRuntime(
            provider=provider,
            tracer=self._tracer,
            executor_factory=self._tool_executor_factory,
        )
        async for event in runtime.stream(
            ChatAgentInput(context=context, message=message),
            api_key=session.api_key,
            config=config,
            effort=session.effort,
            modal_enabled=modal_enabled,
        ):
            if event.type == "progress" and event.progress_kind:
                yield TerminalOutput(
                    kind=event.progress_kind,  # type: ignore[arg-type]
                    content=event.message or "",
                    elapsed_seconds=event.elapsed_seconds,
                )
            elif event.type == "started":
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
