from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import replace

from engine.chat.budget import BudgetedChatPrompt, budget_chat_prompt, budget_context_snapshot
from engine.chat.context import ContextSnapshot
from engine.chat.models import ChatAgentInput, ChatStreamEvent
from engine.llm.config import LLMRequestConfig
from engine.llm.groq import GroqProviderError
from engine.llm.providers import LLMProvider, provider_for
from engine.observability import LangSmithTracer


class ChatAgent:
    """Terminal-first chat agent that can answer with or without report context."""

    def __init__(self, provider: LLMProvider | None = None, tracer: LangSmithTracer | None = None) -> None:
        self._provider = provider or provider_for("groq")
        self._tracer = tracer or LangSmithTracer()

    async def stream(
        self,
        request: ChatAgentInput,
        *,
        api_key: str,
        config: LLMRequestConfig,
    ) -> AsyncIterator[ChatStreamEvent]:
        async with self._tracer.span(
            "groq_model_lookup",
            run_type="llm",
            metadata={"model_id": config.model_id},
            tags=["chat", "groq"],
        ) as span:
            model = await self._provider.retrieve_model(api_key=api_key, model_id=config.model_id)
            span.end({"context_window": model.context_window, "max_completion_tokens": model.max_completion_tokens})
        async with self._tracer.span(
            "prompt_budgeting",
            inputs={"message": self._tracer.text(request.message)},
            metadata={"requested_output_tokens": config.max_output_tokens},
            tags=["chat", "context"],
        ) as span:
            prompt = budget_chat_prompt(
                context=request.context,
                message=request.message,
                model=model,
                requested_output_tokens=config.max_output_tokens,
            )
            span.end({"input_token_upper_bound": prompt.input_token_upper_bound, "context_truncated": prompt.context_truncated})
        async for event in self._stream_prompt(prompt, api_key=api_key, config=config):
            yield event

    async def stream_snapshot(
        self,
        snapshot: ContextSnapshot,
        *,
        api_key: str,
        config: LLMRequestConfig,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Stream a persisted ContextManager snapshot without flattening turns."""
        model = await self._provider.retrieve_model(api_key=api_key, model_id=config.model_id)
        prompt = budget_context_snapshot(
            snapshot=snapshot,
            model=model,
            requested_output_tokens=config.max_output_tokens,
        )
        async for event in self._stream_prompt(prompt, api_key=api_key, config=config):
            yield event

    async def _stream_prompt(
        self,
        prompt: BudgetedChatPrompt,
        *,
        api_key: str,
        config: LLMRequestConfig,
    ) -> AsyncIterator[ChatStreamEvent]:
        effective_config = replace(config, max_output_tokens=prompt.max_output_tokens)
        yield ChatStreamEvent(
            type="started",
            model_id=config.model_id,
            input_token_upper_bound=prompt.input_token_upper_bound,
            max_output_tokens=prompt.max_output_tokens,
            context_truncated=prompt.context_truncated,
        )

        content = ""
        async with self._tracer.span(
            "groq_stream_generation",
            run_type="llm",
            inputs={"messages": self._tracer.text(str(prompt.messages))},
            metadata={
                "model_id": config.model_id,
                "max_output_tokens": effective_config.max_output_tokens,
                "reasoning_effort": config.reasoning_effort,
            },
            tags=["chat", "groq", "stream"],
        ) as span:
            try:
                async for delta in self._provider.stream_chat(
                    api_key=api_key,
                    config=effective_config,
                    messages=prompt.messages,
                ):
                    content += delta
                    yield ChatStreamEvent(type="delta", model_id=config.model_id, delta=delta)
            except GroqProviderError as exc:
                # GPT-OSS can spontaneously emit a tool call on this no-tools
                # answer request; Groq then rejects the turn with "Tool choice
                # is none, but model called a tool" before any text streams.
                # It surfaces the model's failure to any downstream skill (each
                # already ran), so retry the plain answer once. Only safe when
                # nothing has streamed yet, so we never duplicate output.
                if exc.code != "provider_invalid_model_output" or content:
                    raise
                async for delta in self._provider.stream_chat(
                    api_key=api_key,
                    config=effective_config,
                    messages=prompt.messages,
                ):
                    content += delta
                    yield ChatStreamEvent(type="delta", model_id=config.model_id, delta=delta)
            retried_at_low_effort = False
            if not content and effective_config.reasoning_effort not in {None, "low"}:
                # Reasoning tokens and visible text share the completion
                # budget. A GPT-OSS turn can therefore finish after internal
                # reasoning without a visible delta. Retry only that empty
                # case, at low effort, so a normal user response still wins.
                retried_at_low_effort = True
                low_effort_config = replace(effective_config, reasoning_effort="low")
                async for delta in self._provider.stream_chat(
                    api_key=api_key,
                    config=low_effort_config,
                    messages=prompt.messages,
                ):
                    content += delta
                    yield ChatStreamEvent(type="delta", model_id=config.model_id, delta=delta)
            span.end(
                {
                    "response": self._tracer.text(content),
                    "character_count": len(content),
                    "retried_at_low_effort": retried_at_low_effort,
                }
            )

        if not content:
            raise GroqProviderError(
                code="provider_empty_stream",
                message=(
                    f"{config.provider.title()} model {config.model_id} completed the stream "
                    "without visible assistant content"
                ),
                retryable=True,
            )
        yield ChatStreamEvent(type="completed", model_id=config.model_id, content=content)
