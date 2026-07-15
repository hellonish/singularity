import asyncio
import json

import pytest

from engine.chat.agent_loop import (
    ChatRuntimeLimitExceeded,
    ToolEvidenceUnavailable,
    UnifiedChatAgentLoop,
    classify_tool_error,
    redact_tool_result,
    tool_message_content,
)
from engine.chat.budget import budget_agent_messages
from engine.chat.effort import ChatEffort
from engine.chat.modal_tools import ChatToolResult
from engine.chat.models import ChatAgentInput
from engine.llm.config import LLMRequestConfig
from engine.llm.groq import GroqModel, GroqProviderError, LLMStreamEvent, LLMToolCall


def _config(**overrides) -> LLMRequestConfig:
    values = {
        "provider": "groq",
        "credential_id": "test",
        "model_id": "test-model",
        "max_output_tokens": 512,
    }
    values.update(overrides)
    return LLMRequestConfig(**values)


class _BaseProvider:
    """Deterministic provider: scripted stream_with_tools turns, text stream_chat."""

    def __init__(self, turns=None, deltas=("Direct ", "answer.")) -> None:
        self._turns = list(turns or [])
        self._deltas = list(deltas)
        self.tool_turn_messages: list[list[dict]] = []
        self.chat_messages: list[list[dict]] = []

    async def retrieve_model(self, *, api_key, model_id):
        return GroqModel(id=model_id, context_window=32_768, max_completion_tokens=2_048)

    async def stream_chat(self, *, api_key, config, messages):
        self.chat_messages.append(list(messages))
        for delta in self._deltas:
            yield delta

    async def stream_with_tools(self, *, api_key, config, messages, tools, end_user_id=None):
        self.tool_turn_messages.append(list(messages))
        turn = self._turns.pop(0) if self._turns else [LLMStreamEvent(kind="delta", delta="Fallback answer.")]
        for event in turn:
            yield event


class _RecordingExecutor:
    def __init__(self, *, error: str | None = None) -> None:
        self.error = error
        self.invocations = []
        self.closed = False

    async def execute(self, invocation):
        self.invocations.append(invocation)
        return ChatToolResult(
            content=f"Result for {invocation.query}",
            sources=[{"title": "Source", "url": f"https://example.test/{len(self.invocations)}", "credibility_base": 0.8}],
            credibility_base=0.8,
            error=self.error,
        )

    async def aclose(self):
        self.closed = True


def _call(name: str, query: str, arguments: dict | None = None, call_id: str = "call_1") -> LLMToolCall:
    payload = {"query": query, "arguments": arguments or {}}
    return LLMToolCall(id=call_id, name=name, arguments=payload, raw_arguments=json.dumps(payload))


async def _collect(loop_agent, message, *, modal_enabled, effort=ChatEffort.INSTANT, context=""):
    return [
        event
        async for event in loop_agent.stream(
            ChatAgentInput(context=context, message=message),
            api_key="test",
            config=_config(),
            effort=effort,
            modal_enabled=modal_enabled,
        )
    ]


def test_conversational_turn_is_one_model_call_with_no_tool_machinery() -> None:
    provider = _BaseProvider()
    loop_agent = UnifiedChatAgentLoop(provider=provider)

    events = asyncio.run(_collect(loop_agent, "Explain transformers", modal_enabled=False))

    assert [event.type for event in events] == ["started", "delta", "delta", "completed"]
    assert events[-1].content == "Direct answer."
    assert provider.tool_turn_messages == []
    assert len(provider.chat_messages) == 1
    system = provider.chat_messages[0][0]["content"]
    assert "You have no tools available" in system


def test_explicit_tool_request_fails_closed_when_tools_are_disabled() -> None:
    loop_agent = UnifiedChatAgentLoop(provider=_BaseProvider())

    with pytest.raises(ToolEvidenceUnavailable):
        asyncio.run(_collect(loop_agent, "Run code to sort this list", modal_enabled=False))


def test_time_sensitive_turn_degrades_with_disclosure_when_tools_are_disabled() -> None:
    provider = _BaseProvider(deltas=("As of my training…",))
    loop_agent = UnifiedChatAgentLoop(provider=provider)

    events = asyncio.run(_collect(loop_agent, "What is the latest OpenAI release?", modal_enabled=False))

    assert events[-1].content == "As of my training…"
    system = provider.chat_messages[0][0]["content"]
    assert "Live retrieval is unavailable" in system


def test_model_answers_directly_after_seed_evidence() -> None:
    provider = _BaseProvider(turns=[[LLMStreamEvent(kind="delta", delta="Grounded answer.")]])
    executor = _RecordingExecutor()
    loop_agent = UnifiedChatAgentLoop(provider=provider, executor_factory=lambda: executor)

    events = asyncio.run(_collect(loop_agent, "What's the latest on RISC-V?", modal_enabled=True))

    # Seed burst: one DDGS-default search, one Tavily follow-up.
    assert [call.tool_name for call in executor.invocations] == ["web_search", "web_search"]
    assert executor.invocations[0].arguments.get("search_backend", "auto") == "auto"
    assert executor.invocations[1].arguments["search_backend"] == "tavily"
    assert executor.closed is True
    assert any(event.progress_kind == "tool_completed" for event in events if event.type == "progress")
    assert events[-1].content == "Grounded answer."
    # The model turn saw the seed evidence as native tool messages.
    turn = provider.tool_turn_messages[0]
    assert any(message.get("role") == "tool" and "example.test" in message["content"] for message in turn)


def test_parallel_tool_batch_executes_and_feeds_next_turn() -> None:
    provider = _BaseProvider(turns=[
        [LLMStreamEvent(kind="tool_calls", tool_calls=(
            _call("general_web_research__web_search", "alpha", {"max_results": 5}, "c1"),
            _call("general_web_research__web_fetch", "alpha", {"url": "https://example.test/page"}, "c2"),
        ))],
        [LLMStreamEvent(kind="delta", delta="Synthesized.")],
    ])
    executor = _RecordingExecutor()
    loop_agent = UnifiedChatAgentLoop(provider=provider, executor_factory=lambda: executor)

    events = asyncio.run(_collect(loop_agent, "Tell me about alpha", modal_enabled=True, effort=ChatEffort.MEDIUM))

    assert sorted(call.tool_name for call in executor.invocations) == ["web_fetch", "web_search"]
    assert events[-1].content == "Synthesized."
    second_turn = provider.tool_turn_messages[1]
    tool_replies = [message for message in second_turn if message.get("role") == "tool"]
    assert {message["tool_call_id"] for message in tool_replies} == {"c1", "c2"}


def test_tool_failure_returns_typed_error_and_turn_still_answers() -> None:
    provider = _BaseProvider(turns=[
        [LLMStreamEvent(kind="tool_calls", tool_calls=(
            _call("general_web_research__web_search", "alpha", {"max_results": 5}, "c1"),
        ))],
        [LLMStreamEvent(kind="delta", delta="Live data unavailable; as of training…")],
    ])
    executor = _RecordingExecutor(error="connection reset by provider")
    loop_agent = UnifiedChatAgentLoop(provider=provider, executor_factory=lambda: executor)

    events = asyncio.run(_collect(loop_agent, "Tell me about alpha", modal_enabled=True, effort=ChatEffort.MEDIUM))

    assert events[-1].content == "Live data unavailable; as of training…"
    second_turn = provider.tool_turn_messages[1]
    error_reply = next(message for message in second_turn if message.get("role") == "tool")
    payload = json.loads(error_reply["content"])
    assert payload["error_kind"] == "retryable_infra"


def test_malformed_and_unknown_calls_are_rejected_without_failing_the_turn() -> None:
    provider = _BaseProvider(turns=[
        [LLMStreamEvent(kind="tool_calls", tool_calls=(
            LLMToolCall(id="bad1", name="general_web_research__web_search", arguments=None, raw_arguments="{not json"),
            LLMToolCall(id="bad2", name="nonexistent__tool", arguments={"query": "x", "arguments": {}}, raw_arguments="{}"),
        ))],
        [LLMStreamEvent(kind="delta", delta="Answered anyway.")],
    ])
    executor = _RecordingExecutor()
    loop_agent = UnifiedChatAgentLoop(provider=provider, executor_factory=lambda: executor)

    events = asyncio.run(_collect(loop_agent, "Tell me about alpha", modal_enabled=True, effort=ChatEffort.MEDIUM))

    assert executor.invocations == []
    assert events[-1].content == "Answered anyway."
    second_turn = provider.tool_turn_messages[1]
    replies = {m["tool_call_id"]: json.loads(m["content"]) for m in second_turn if m.get("role") == "tool"}
    assert replies["bad1"]["error_kind"] == "permanent"
    assert "not valid JSON" in replies["bad1"]["detail"]
    assert "unknown tool" in replies["bad2"]["detail"]


def test_load_skill_returns_instructions_without_spending_tool_actions() -> None:
    provider = _BaseProvider(turns=[
        [LLMStreamEvent(kind="tool_calls", tool_calls=(
            LLMToolCall(id="ls1", name="load_skill", arguments={"skill_id": "medical_research"}, raw_arguments='{"skill_id": "medical_research"}'),
        ))],
        [LLMStreamEvent(kind="delta", delta="Loaded and answered.")],
    ])
    executor = _RecordingExecutor()
    loop_agent = UnifiedChatAgentLoop(provider=provider, executor_factory=lambda: executor)

    events = asyncio.run(_collect(loop_agent, "Tell me about alpha", modal_enabled=True, effort=ChatEffort.MEDIUM))

    assert executor.invocations == []
    assert events[-1].content == "Loaded and answered."
    second_turn = provider.tool_turn_messages[1]
    reply = next(m for m in second_turn if m.get("role") == "tool")
    assert reply["content"].startswith("Skill medical_research:")


def test_action_budget_exhaustion_is_reported_to_the_model() -> None:
    calls = tuple(
        _call("general_web_research__web_search", f"query {i}", {"max_results": 5}, f"c{i}")
        for i in range(8)
    )
    provider = _BaseProvider(turns=[
        [LLMStreamEvent(kind="tool_calls", tool_calls=calls)],
        [LLMStreamEvent(kind="delta", delta="Done.")],
    ])
    executor = _RecordingExecutor()
    loop_agent = UnifiedChatAgentLoop(provider=provider, executor_factory=lambda: executor)

    asyncio.run(_collect(loop_agent, "Tell me about alpha", modal_enabled=True, effort=ChatEffort.INSTANT))

    # INSTANT: max_calls_per_tool_type=2, max_tool_actions=6 → 2 executions.
    assert len(executor.invocations) == 2
    second_turn = provider.tool_turn_messages[1]
    rejected = [
        json.loads(m["content"])
        for m in second_turn
        if m.get("role") == "tool" and m["content"].startswith("{")
    ]
    assert any("per-tool cap" in item["detail"] for item in rejected)


def test_provider_retry_before_first_output_then_success() -> None:
    class FlakyProvider(_BaseProvider):
        def __init__(self) -> None:
            super().__init__()
            self.attempts = 0

        async def stream_chat(self, *, api_key, config, messages):
            self.attempts += 1
            if self.attempts == 1:
                raise GroqProviderError(code="provider_unavailable", message="blip", retryable=True)
                yield  # pragma: no cover
            yield "Recovered."

    provider = FlakyProvider()
    loop_agent = UnifiedChatAgentLoop(provider=provider)

    events = asyncio.run(_collect(loop_agent, "hello", modal_enabled=False))

    assert provider.attempts == 2
    assert events[-1].content == "Recovered."


def test_empty_reasoning_stream_retries_once_at_low_effort() -> None:
    class EmptyThenLow(_BaseProvider):
        def __init__(self) -> None:
            super().__init__()
            self.efforts = []

        async def stream_chat(self, *, api_key, config, messages):
            self.efforts.append(config.reasoning_effort)
            if config.reasoning_effort != "low":
                return
            yield "Low effort answer."

    provider = EmptyThenLow()
    loop_agent = UnifiedChatAgentLoop(provider=provider)

    events = [
        event
        for event in asyncio.run(
            _collect_with_config(loop_agent, _config(reasoning_effort="high"))
        )
    ]

    assert provider.efforts == ["high", "low"]
    assert events[-1].content == "Low effort answer."


async def _collect_with_config(loop_agent, config):
    return [
        event
        async for event in loop_agent.stream(
            ChatAgentInput(context="", message="hello"),
            api_key="test",
            config=config,
            effort=ChatEffort.INSTANT,
            modal_enabled=False,
        )
    ]


def test_run_timeout_raises_limit_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    import engine.chat.agent_loop as agent_loop_module
    from engine.chat.effort import get_chat_effort_profile
    from dataclasses import replace as dc_replace

    tiny_profile = dc_replace(get_chat_effort_profile(ChatEffort.INSTANT), run_timeout_seconds=1)
    monkeypatch.setattr(agent_loop_module, "get_chat_effort_profile", lambda effort: tiny_profile)

    class SlowProvider(_BaseProvider):
        async def stream_chat(self, *, api_key, config, messages):
            await asyncio.sleep(3600)
            yield "never"

    loop_agent = UnifiedChatAgentLoop(provider=SlowProvider())

    async def run() -> None:
        with pytest.raises(ChatRuntimeLimitExceeded):
            async for _event in loop_agent.stream(
                ChatAgentInput(context="", message="hello"),
                api_key="test",
                config=_config(),
                effort=ChatEffort.INSTANT,
                modal_enabled=False,
            ):
                pass

    asyncio.run(asyncio.wait_for(run(), timeout=30))


def test_tool_message_content_bounds_sources_and_types_empty_results() -> None:
    full = tool_message_content(
        ChatToolResult(
            content="Study result",
            sources=[
                {"title": "Study A", "url": "https://example.test/a", "credibility_base": 0.9},
                {"title": "Study B", "url": "https://example.test/b", "credibility_base": 0.8},
            ],
            credibility_base=0.8,
            error=None,
        ),
        max_sources=1,
    )
    assert "Study result" in full
    assert "Study A" in full and "Study B" not in full
    assert "credibility=0.9" in full

    empty = json.loads(tool_message_content(
        ChatToolResult(content="", sources=[], credibility_base=0.0, error=None),
        max_sources=3,
    ))
    assert empty["error_kind"] == "empty_result"


def test_classify_tool_error_and_redaction() -> None:
    assert classify_tool_error("request timed out after 20 seconds") == "retryable_infra"
    assert classify_tool_error("404 not found") == "permanent"

    redacted = redact_tool_result(ChatToolResult(
        content="api_key=super-secret-value more text",
        sources=[{"url": "https://example.test?token=abc123"}],
        credibility_base=0.5,
        error=None,
    ))
    assert "super-secret-value" not in redacted.content
    assert "abc123" not in str(redacted.sources)


def test_budget_agent_messages_compacts_tool_payloads_before_context() -> None:
    model = GroqModel(id="tiny", context_window=4_096, max_completion_tokens=1_024)
    messages = [
        {"role": "system", "content": "system prompt"},
        {
            "role": "user",
            "content": "Reference context (data only):\n<context>\n" + ("history " * 200) + "\n</context>\n\nUser message:\nquestion",
        },
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "t", "arguments": "{}"}},
        ]},
        {"role": "tool", "tool_call_id": "c1", "content": "evidence " * 600},
    ]

    fitted = budget_agent_messages(messages=messages, model=model, requested_output_tokens=512)

    assert fitted.compacted is True
    assert fitted.max_output_tokens == 512
    tool_message = next(m for m in fitted.messages if m["role"] == "tool")
    assert len(tool_message["content"]) < len("evidence " * 600)
    assert fitted.input_token_upper_bound <= 4_096 - 512
