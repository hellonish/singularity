from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace

from engine.chat.budget import BudgetedChatPrompt, budget_chat_prompt, budget_context_snapshot
from engine.chat.context import ContextSnapshot
from engine.chat.models import ChatAgentInput, ChatStreamEvent
from engine.chat.model_capabilities import MODEL_CAPABILITIES, ModelCapabilityRegistry
from engine.chat.retry import RetryPolicy
from engine.llm.config import LLMRequestConfig
from engine.llm.groq import GroqProviderError
from engine.llm.providers import LLMProvider, provider_for
from engine.observability import LangSmithTracer


class ChatAgent:
    """Terminal-first chat agent that can answer with or without report context."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        tracer: LangSmithTracer | None = None,
        capability_registry: ModelCapabilityRegistry | None = None,
    ) -> None:
        self._provider = provider or provider_for("groq")
        self._tracer = tracer or LangSmithTracer()
        self._capability_registry = capability_registry or MODEL_CAPABILITIES

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
            capabilities = await self._capability_registry.resolve(
                provider_name=config.provider,
                provider=self._provider,
                api_key=api_key,
                model_id=config.model_id,
            )
            model = capabilities.as_model()
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
        capabilities = await self._capability_registry.resolve(
            provider_name=config.provider,
            provider=self._provider,
            api_key=api_key,
            model_id=config.model_id,
        )
        model = capabilities.as_model()
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
            stream_retry = RetryPolicy(max_retries=2, base_delay_seconds=0.5, max_delay_seconds=4.0)
            model_retry_count = 0
            for attempt in range(stream_retry.max_retries + 1):
                try:
                    async for delta in self._provider.stream_chat(
                        api_key=api_key,
                        config=effective_config,
                        messages=prompt.messages,
                    ):
                        content += delta
                        yield ChatStreamEvent(type="delta", model_id=config.model_id, delta=delta)
                except GroqProviderError as exc:
                    # Streaming retries are only safe before the first visible
                    # delta. Never duplicate a partial answer.
                    if content or not exc.retryable or attempt >= stream_retry.max_retries:
                        raise
                    model_retry_count += 1
                    try:
                        delay = float(exc.retry_after_seconds) if exc.retry_after_seconds else stream_retry.delay(attempt)
                    except (TypeError, ValueError):
                        delay = stream_retry.delay(attempt)
                    await asyncio.sleep(min(8.0, max(0.0, delay)))
                    continue
                break
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
                    "model_retry_count": model_retry_count,
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
