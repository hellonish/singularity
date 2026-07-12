from __future__ import annotations

import os

import pytest

from engine.chat import ChatAgent, ChatAgentInput, ContextSnapshot
from engine.chat.budget import CONTEXT_SAFETY_TOKENS, ChatInputTooLarge, budget_chat_prompt
from engine.chat.context import ContextTurn, SummaryContext
from engine.llm.config import LLMRequestConfig
from engine.llm.groq import GroqModel


class _FakeProvider:
    def __init__(self) -> None:
        self.messages = None

    async def retrieve_model(self, *, api_key: str, model_id: str) -> GroqModel:
        return GroqModel(id=model_id, context_window=8_192, max_completion_tokens=1_024, active=True)

    async def stream_chat(self, *, api_key: str, config, messages):
        self.messages = messages
        yield "context-aware"


class _ReasoningOnlyProvider(_FakeProvider):
    def __init__(self) -> None:
        super().__init__()
        self.efforts: list[str | None] = []

    async def stream_chat(self, *, api_key: str, config, messages):
        self.efforts.append(config.reasoning_effort)
        if config.reasoning_effort == "low":
            yield "visible response"


def test_context_is_trimmed_and_total_budget_stays_inside_model_window() -> None:
    model = GroqModel(
        id="arbitrary-groq-model",
        context_window=1024,
        max_completion_tokens=256,
        active=True,
    )
    prompt = budget_chat_prompt(
        context="report context " * 500,
        message="Summarize the report.",
        model=model,
        requested_output_tokens=128,
    )
    assert prompt.context_truncated is True
    assert prompt.input_token_upper_bound + prompt.max_output_tokens + CONTEXT_SAFETY_TOKENS <= 1024
    assert "Summarize the report." in prompt.messages[-1]["content"]


def test_message_is_never_silently_truncated() -> None:
    model = GroqModel(
        id="arbitrary-groq-model",
        context_window=512,
        max_completion_tokens=128,
        active=True,
    )
    with pytest.raises(ChatInputTooLarge):
        budget_chat_prompt(
            context="",
            message="x" * 2000,
            model=model,
            requested_output_tokens=128,
        )


@pytest.mark.asyncio
async def test_agent_streams_a_context_snapshot_as_role_preserving_messages() -> None:
    provider = _FakeProvider()
    agent = ChatAgent(provider=provider)
    snapshot = ContextSnapshot(
        chat_id="chat_1",
        report=None,
        summary=SummaryContext("summary_1", 1, None, 0, "Earlier discussion.", 3),
        turns=(
            ContextTurn("message_1", 1, "user", "Earlier question"),
            ContextTurn("message_2", 2, "assistant", "Earlier answer"),
            ContextTurn("message_3", 3, "user", "Current question"),
        ),
        latest_message_id="message_3",
    )
    events = [
        event
        async for event in agent.stream_snapshot(
            snapshot,
            api_key="test-key",
            config=LLMRequestConfig(
                provider="groq", credential_id="cred_1", model_id="test-model", max_output_tokens=256
            ),
        )
    ]

    assert provider.messages is not None
    assert provider.messages[-1] == {"role": "user", "content": "Current question"}
    assert provider.messages[-2] == {"role": "assistant", "content": "Earlier answer"}
    assert events[-1].content == "context-aware"


@pytest.mark.asyncio
async def test_agent_retries_a_reasoning_only_stream_at_low_effort() -> None:
    provider = _ReasoningOnlyProvider()
    events = [
        event
        async for event in ChatAgent(provider=provider).stream(
            ChatAgentInput(context="", message="Reply briefly."),
            api_key="test-key",
            config=LLMRequestConfig(
                provider="groq",
                credential_id="cred_1",
                model_id="openai/gpt-oss-20b",
                max_output_tokens=256,
                reasoning_effort="medium",
            ),
        )
    ]

    assert provider.efforts == ["medium", "low"]
    assert events[-1].content == "visible response"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_chat_agent_streams_real_groq_deltas() -> None:
    if os.getenv("SINGULARITY_RUN_LIVE_TESTS") != "1":
        pytest.skip("Set SINGULARITY_RUN_LIVE_TESTS=1 to allow live Groq tests")
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("SINGULARITY_TEST_GROQ_API_KEY")
    if not api_key:
        pytest.skip("Set GROQ_API_KEY to run the live chat engine test")

    events = []
    async for event in ChatAgent().stream(
        ChatAgentInput(context="The expected keyword is pong.", message="Reply briefly with the expected keyword."),
        api_key=api_key,
        config=LLMRequestConfig(
            provider="groq",
            credential_id="terminal-test",
            model_id="openai/gpt-oss-20b",
            temperature=0.0,
            max_output_tokens=256,
        ),
    ):
        events.append(event)

    assert events[0].type == "started"
    deltas = [event.delta for event in events if event.type == "delta"]
    assert deltas and all(deltas)
    assert events[-1].type == "completed"
    assert events[-1].content == "".join(deltas)
