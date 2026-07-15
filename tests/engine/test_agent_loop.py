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
        self.tool_schemas: list[list[dict]] = []
        self.chat_messages: list[list[dict]] = []

    async def retrieve_model(self, *, api_key, model_id):
        return GroqModel(id=model_id, context_window=32_768, max_completion_tokens=2_048)

    async def stream_chat(self, *, api_key, config, messages):
        self.chat_messages.append(list(messages))
        for delta in self._deltas:
            yield delta

    async def stream_with_tools(self, *, api_key, config, messages, tools, end_user_id=None):
        self.tool_turn_messages.append(list(messages))
        self.tool_schemas.append(list(tools))
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


def test_non_sandbox_tool_request_still_fails_closed_when_tools_disabled() -> None:
    # A non-sandbox explicit tool request (e.g. live web lookup) with all tools
    # off has no code to hand back, so it still fails closed rather than degrade.
    loop_agent = UnifiedChatAgentLoop(provider=_BaseProvider())

    with pytest.raises(ToolEvidenceUnavailable):
        asyncio.run(_collect(
            loop_agent, "Look up the PubMed article on aspirin", modal_enabled=False
        ))


def test_required_sandbox_with_tools_disabled_degrades_gracefully() -> None:
    # The Sandbox cannot run with tools off. Rather than a hard error in chat,
    # the model answers directly (returns the code and guidance to run it).
    provider = _BaseProvider(deltas=("Could not run it; here is the code…",))
    loop_agent = UnifiedChatAgentLoop(provider=provider)

    events = asyncio.run(_collect(loop_agent, "Run code to sort this list", modal_enabled=False))

    assert events[-1].type == "completed"
    assert events[-1].content == "Could not run it; here is the code…"
    # The degraded turn is text-only and seeded with the degradation note.
    system_notes = [
        message["content"]
        for message in provider.chat_messages[0]
        if message.get("role") == "system"
    ]
    assert any("could not run this request" in note for note in system_notes)


def test_repository_request_preloads_only_relevant_sandbox_schemas() -> None:
    provider = _BaseProvider(turns=[
        [LLMStreamEvent(kind="tool_calls", tool_calls=(
            _call(
                "repository_inspection__repository_inspection",
                "inspect repository",
                {"repository_url": "https://github.com/openai/openai-python", "operations": ["files"]},
            ),
        ))],
        [LLMStreamEvent(kind="delta", delta="Repository-grounded answer.")],
    ])
    executor = _RecordingExecutor()
    loop_agent = UnifiedChatAgentLoop(provider=provider, executor_factory=lambda: executor)

    events = asyncio.run(_collect(
        loop_agent,
        "Inspect https://github.com/openai/openai-python",
        modal_enabled=True,
        effort=ChatEffort.MEDIUM,
    ))

    names = {schema["function"]["name"] for schema in provider.tool_schemas[0]}
    assert "repository_inspection__repository_inspection" in names
    assert "sandbox_workspace__sandbox_create" in names
    assert "medical_research__pubmed" not in names
    assert "load_skill" in names
    assert executor.invocations[0].tool_name == "repository_inspection"
    assert events[-1].content == "Repository-grounded answer."
    system = provider.tool_turn_messages[0][0]["content"]
    assert "Repository-specific claims require evidence from a Modal Sandbox" in system


def test_required_evidence_degrades_gracefully_after_sandbox_error() -> None:
    # The Sandbox was attempted and failed (no usable evidence). The model's
    # unsupported answer is discarded and the turn degrades: a text-only reply
    # that explains it could not run, returns the code, and points to resources.
    provider = _BaseProvider(
        turns=[
            [LLMStreamEvent(kind="tool_calls", tool_calls=(
                _call(
                    "repository_inspection__repository_inspection",
                    "inspect repository",
                    {"repository_url": "https://github.com/openai/openai-python", "operations": ["files"]},
                ),
            ))],
            [LLMStreamEvent(kind="delta", delta="Unsupported answer.")],
        ],
        deltas=("I could not inspect it; here is how to run it yourself…",),
    )
    executor = _RecordingExecutor(error="sandbox unavailable")
    loop_agent = UnifiedChatAgentLoop(provider=provider, executor_factory=lambda: executor)

    events = asyncio.run(_collect(
        loop_agent,
        "Inspect https://github.com/openai/openai-python",
        modal_enabled=True,
        effort=ChatEffort.MEDIUM,
    ))

    assert events[-1].type == "completed"
    assert events[-1].content == "I could not inspect it; here is how to run it yourself…"
    # The unsupported model answer never reached the user.
    assert all(event.content != "Unsupported answer." for event in events if event.type == "completed")
    # The failed workspace was closed before degrading.
    assert executor.closed is True
    system_notes = [
        message["content"]
        for message in provider.chat_messages[0]
        if message.get("role") == "system"
    ]
    assert any("could not run this request" in note for note in system_notes)


class _SandboxExecutor:
    """Executor whose sandbox actually runs the command (executed=True)."""

    def __init__(self, *, error: str | None, content: str = "{}") -> None:
        self._error = error
        self._content = content
        self.invocations: list = []
        self.closed = False

    async def execute(self, invocation):
        self.invocations.append(invocation)
        return ChatToolResult(
            content=self._content,
            sources=[{
                "title": "Validated isolated code execution",
                "url": "",
                "source_type": "sandbox_execution",
                "credibility_base": 1.0,
            }],
            credibility_base=1.0 if self._error is None else 0.0,
            error=self._error,
            executed=True,
        )

    async def aclose(self):
        self.closed = True


def test_code_level_sandbox_error_is_evidence_and_turn_answers() -> None:
    # The Sandbox ran the code and it exited non-zero (e.g. ModuleNotFoundError).
    # That is verifiable evidence: the model must be allowed to react and answer
    # instead of the whole turn failing closed.
    provider = _BaseProvider(turns=[
        [LLMStreamEvent(kind="tool_calls", tool_calls=(
            _call(
                "code_execution__code_execution",
                "run the script",
                {"files": {"main.py": "import numpy"}, "command": ["python", "main.py"]},
            ),
        ))],
        [LLMStreamEvent(
            kind="delta",
            delta="The script failed with ModuleNotFoundError: No module named 'numpy'.",
        )],
    ])
    executor = _SandboxExecutor(
        error="code execution exited with code 1",
        content='{"exit_code": 1, "stderr": "ModuleNotFoundError: No module named \'numpy\'"}',
    )
    loop_agent = UnifiedChatAgentLoop(provider=provider, executor_factory=lambda: executor)

    events = asyncio.run(_collect(
        loop_agent,
        "Run this python code and show the output",
        modal_enabled=True,
        effort=ChatEffort.MEDIUM,
    ))

    assert executor.invocations[0].tool_name == "code_execution"
    assert events[-1].content == (
        "The script failed with ModuleNotFoundError: No module named 'numpy'."
    )
    error_reply = next(
        message for message in provider.tool_turn_messages[1] if message.get("role") == "tool"
    )
    assert "ModuleNotFoundError" in error_reply["content"]


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

    events = asyncio.run(_collect(loop_agent, "What's the latest on RISC-V instruction set architecture?", modal_enabled=True))

    # Lightweight Chat spends one discovery call before the model decides if a
    # fetch or refinement is needed.
    assert [call.tool_name for call in executor.invocations] == ["web_search"]
    assert executor.invocations[0].arguments.get("search_backend", "auto") == "auto"
    assert executor.closed is True
    assert any(event.progress_kind == "tool_completed" for event in events if event.type == "progress")
    assert events[-1].content == "Grounded answer."
    # The model turn saw the seed evidence as native tool messages.
    turn = provider.tool_turn_messages[0]
    assert any(message.get("role") == "tool" and "example.test" in message["content"] for message in turn)


def test_ambiguous_named_entity_asks_before_any_search_or_model_call() -> None:
    provider = _BaseProvider()
    executor = _RecordingExecutor()
    loop_agent = UnifiedChatAgentLoop(provider=provider, executor_factory=lambda: executor)

    events = asyncio.run(_collect(loop_agent, "Search for Apple", modal_enabled=True))

    assert executor.invocations == []
    assert provider.tool_turn_messages == []
    assert provider.chat_messages == []
    assert [event.type for event in events] == ["started", "completed"]
    assert "Which Apple do you mean?" in (events[-1].content or "")


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
    first_names = {schema["function"]["name"] for schema in provider.tool_schemas[0]}
    second_names = {schema["function"]["name"] for schema in provider.tool_schemas[1]}
    assert "medical_research__pubmed" not in first_names
    assert "medical_research__pubmed" in second_names


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
