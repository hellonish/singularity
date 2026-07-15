import asyncio
import json

from engine.chat.effort import ChatEffort
from engine.chat.modal_tools import ChatToolResult
from engine.cli.agents import ChatTerminalAgent
from engine.cli.models import TerminalSession
from engine.llm.groq import GroqModel, LLMStreamEvent, LLMToolCall


class CapturingProvider:
    """Answers on the first model turn; records everything it was shown."""

    def __init__(self) -> None:
        self.tool_turn_messages: list[list[dict]] = []
        self.chat_messages: list[list[dict]] = []

    async def retrieve_model(self, *, api_key, model_id):
        return GroqModel(id=model_id, context_window=32_768, max_completion_tokens=2_000)

    async def stream_chat(self, *, api_key, config, messages):
        self.chat_messages.append(list(messages))
        yield "Grounded current answer."

    async def stream_with_tools(self, *, api_key, config, messages, tools, end_user_id=None):
        self.tool_turn_messages.append(list(messages))
        yield LLMStreamEvent(kind="delta", delta="Grounded current answer.")


class LiveSearchExecutor:
    def __init__(self, *, error=None) -> None:
        self.error = error
        self.invocations = []
        self.closed = False

    async def execute(self, invocation):
        self.invocations.append(invocation)
        return ChatToolResult(
            content=f"Current source summary for {invocation.query}",
            sources=[{"title": f"Current source for {invocation.query}", "url": "https://example.test/current", "credibility_base": 0.8}],
            credibility_base=0.8,
            error=self.error,
        )

    async def aclose(self):
        self.closed = True


def _session() -> TerminalSession:
    return TerminalSession(api_key="test", effort=ChatEffort.INSTANT)


def test_current_events_chat_dispatches_search_and_injects_sources(monkeypatch) -> None:
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "1")
    provider = CapturingProvider()
    executor = LiveSearchExecutor()
    agent = ChatTerminalAgent(provider=provider, tool_executor_factory=lambda: executor)

    outputs = asyncio.run(_collect(agent, "What's going on with Anthropic and OpenAI?"))

    assert [call.tool_name for call in executor.invocations] == ["web_search"]
    assert executor.invocations[0].arguments.get("search_backend", "auto") == "auto"
    assert executor.closed is True
    assert any(output.kind == "tool_completed" for output in outputs)
    assert provider.tool_turn_messages, "answer model never ran"
    assert "https://example.test/current" in str(provider.tool_turn_messages[0])


def test_failed_search_degrades_to_disclosed_answer_instead_of_failing(monkeypatch) -> None:
    """A tool outage on a time-sensitive turn discloses; it no longer dead-ends."""
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "1")
    provider = CapturingProvider()
    executor = LiveSearchExecutor(error="provider unavailable")
    agent = ChatTerminalAgent(provider=provider, tool_executor_factory=lambda: executor)

    outputs = asyncio.run(_collect(agent, "What's going on with Anthropic and OpenAI?"))

    assert executor.closed is True
    assert any(output.kind == "completed" for output in outputs)
    # The model saw the failures as typed error tool messages it can react to.
    turn = provider.tool_turn_messages[0]
    error_payloads = [
        json.loads(message["content"])
        for message in turn
        if message.get("role") == "tool" and message["content"].startswith("{")
    ]
    assert error_payloads and all("error_kind" in payload for payload in error_payloads)


def test_required_sandbox_without_modal_degrades_to_code_and_guidance(monkeypatch) -> None:
    # With Modal off, a code-execution request cannot run in the Sandbox. Rather
    # than dead-ending with an error, the terminal agent streams a degraded
    # answer: the model explains it could not run it and hands back the code.
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "0")
    provider = CapturingProvider()
    agent = ChatTerminalAgent(provider=provider)

    outputs = asyncio.run(_collect(agent, "Run code to sort this list of numbers"))

    assert any(output.kind == "delta" and output.content for output in outputs)
    assert outputs[-1].kind == "completed"
    # The degraded turn is text-only (no tool planning) and seeded with the note.
    assert provider.tool_turn_messages == []
    assert provider.chat_messages, "degraded model turn never ran"
    system_notes = [
        message["content"]
        for message in provider.chat_messages[0]
        if message.get("role") == "system"
    ]
    assert any("could not run this request" in note for note in system_notes)


def test_job_search_and_retry_follow_up_dispatch_fresh_searches(monkeypatch) -> None:
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "1")
    provider = CapturingProvider()
    executor = LiveSearchExecutor()
    agent = ChatTerminalAgent(provider=provider, tool_executor_factory=lambda: executor)
    session = _session()
    request = "Can you find me Job Postings in past 7 days for New Grad SWE?"

    asyncio.run(_collect_with_session(agent, request, session))
    retry_outputs = asyncio.run(_collect_with_session(agent, "Can you try now?", session))

    assert [call.query for call in executor.invocations] == [request, request]
    assert any(output.kind == "routing" for output in retry_outputs)
    assert request in str(provider.tool_turn_messages[-1])


class FollowUpToolCallingProvider(CapturingProvider):
    """Model that requests a search for a non-heuristic follow-up, then answers."""

    async def stream_with_tools(self, *, api_key, config, messages, tools, end_user_id=None):
        self.tool_turn_messages.append(list(messages))
        if len(self.tool_turn_messages) == 1:
            arguments = json.dumps({
                "query": "new grad SWE job postings individual listings",
                "arguments": {"max_results": 8},
            })
            yield LLMStreamEvent(kind="tool_calls", tool_calls=(
                LLMToolCall(
                    id="c1",
                    name="general_web_research__web_search",
                    arguments=json.loads(arguments),
                    raw_arguments=arguments,
                ),
            ))
            return
        yield LLMStreamEvent(kind="delta", delta="Grounded current answer.")


def test_elliptical_follow_up_lets_the_model_plan_its_own_search(monkeypatch) -> None:
    """A follow-up no heuristic matches must still get live retrieval via the model."""
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "1")
    provider = FollowUpToolCallingProvider()
    executor = LiveSearchExecutor()
    agent = ChatTerminalAgent(provider=provider, tool_executor_factory=lambda: executor)

    outputs = asyncio.run(_collect(agent, "Can you find me the postings instead of just the portals."))

    assert [call.tool_name for call in executor.invocations] == ["web_search"]
    assert "No deterministic heuristic matched" in str(provider.tool_turn_messages[0])
    assert "https://example.test/current" in str(provider.tool_turn_messages[1])
    assert any(output.kind == "tool_completed" for output in outputs)


async def _collect(agent: ChatTerminalAgent, message: str):
    return [output async for output in agent.stream(message=message, session=_session())]


async def _collect_with_session(agent: ChatTerminalAgent, message: str, session: TerminalSession):
    return [output async for output in agent.stream(message=message, session=session)]
