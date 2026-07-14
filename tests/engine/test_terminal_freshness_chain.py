import asyncio
from types import SimpleNamespace

from engine.chat.effort import ChatEffort
from engine.chat.modal_tools import ChatToolResult
from engine.cli.agents import ChatTerminalAgent, FreshnessEvidenceUnavailable
from engine.cli.models import TerminalSession
from engine.llm.groq import GroqModel


class CapturingProvider:
    def __init__(self) -> None:
        self.messages = None
        self.planner_messages = []

    async def retrieve_model(self, *, api_key, model_id):
        return GroqModel(id=model_id, context_window=32_768, max_completion_tokens=2_000)

    async def plan_tool_call(self, *, api_key, config, messages, tools, end_user_id=None):
        # After the seeded discovery burst the model planner decides the next
        # step; returning None means the seed evidence is sufficient.
        self.planner_messages.append(messages)
        return None

    async def stream_chat(self, *, api_key, config, messages):
        self.messages = messages
        yield "Grounded current answer."


class LiveSearchExecutor:
    def __init__(self, *, error=None) -> None:
        self.error = error
        self.invocations = []
        self.closed = False

    async def execute(self, invocation):
        self.invocations.append(invocation)
        return ChatToolResult(
            content="Current source summary",
            sources=[{"title": "Current source", "url": "https://example.test/current", "credibility_base": 0.8}],
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

    assert [call.tool_name for call in executor.invocations] == ["web_search", "web_search"]
    assert executor.invocations[0].arguments.get("search_backend", "auto") == "auto"
    assert executor.invocations[1].arguments["search_backend"] == "tavily"
    assert executor.closed is True
    assert any(output.kind == "tool_completed" for output in outputs)
    assert provider.messages is not None
    assert "https://example.test/current" in str(provider.messages)


def test_current_events_chat_fails_closed_when_search_fails(monkeypatch) -> None:
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "1")
    provider = CapturingProvider()
    executor = LiveSearchExecutor(error="provider unavailable")
    agent = ChatTerminalAgent(provider=provider, tool_executor_factory=lambda: executor)

    try:
        asyncio.run(_collect(agent, "What's going on with Anthropic and OpenAI?"))
    except FreshnessEvidenceUnavailable as exc:
        assert "no usable sources" in str(exc)
    else:
        raise AssertionError("expected freshness request to fail closed")

    assert provider.messages is None
    assert executor.closed is True


def test_job_search_and_retry_follow_up_dispatch_fresh_searches(monkeypatch) -> None:
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "1")
    provider = CapturingProvider()
    executor = LiveSearchExecutor()
    agent = ChatTerminalAgent(provider=provider, tool_executor_factory=lambda: executor)
    session = _session()
    request = "Can you find me Job Postings in past 7 days for New Grad SWE?"

    asyncio.run(_collect_with_session(agent, request, session))
    retry_outputs = asyncio.run(_collect_with_session(agent, "Can you try now?", session))

    assert [call.query for call in executor.invocations] == [request, f"{request} official primary sources"] * 2
    assert any(output.kind == "routing" for output in retry_outputs)
    assert provider.messages is not None
    assert request in str(provider.messages)


class FollowUpPlanningProvider(CapturingProvider):
    """Model planner that requests a search for a non-heuristic follow-up."""

    async def plan_tool_call(self, *, api_key, config, messages, tools, end_user_id=None):
        self.planner_messages.append(messages)
        if len(self.planner_messages) > 1:
            return None
        return SimpleNamespace(
            name="general_web_research__web_search",
            arguments={
                "query": "new grad SWE job postings individual listings",
                "arguments": {"max_results": 8},
            },
        )


class FailingPlanningProvider(CapturingProvider):
    async def plan_tool_call(self, *, api_key, config, messages, tools, end_user_id=None):
        raise RuntimeError("planner unavailable")


def test_elliptical_follow_up_reaches_model_planner_and_injects_evidence(monkeypatch) -> None:
    """A follow-up no heuristic matches must still get a planning chance."""
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "1")
    provider = FollowUpPlanningProvider()
    executor = LiveSearchExecutor()
    agent = ChatTerminalAgent(provider=provider, tool_executor_factory=lambda: executor)

    outputs = asyncio.run(_collect(agent, "Can you find me the postings instead of just the portals."))

    assert [call.tool_name for call in executor.invocations] == ["web_search"]
    assert provider.planner_messages, "model planner was never consulted"
    assert "No deterministic heuristic matched" in str(provider.planner_messages[0])
    assert "https://example.test/current" in str(provider.messages)
    assert any(output.kind == "tool_completed" for output in outputs)


def test_optional_planning_failure_degrades_to_direct_answer(monkeypatch) -> None:
    """Planner errors must not block turns the heuristics never marked live."""
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "1")
    provider = FailingPlanningProvider()
    executor = LiveSearchExecutor()
    agent = ChatTerminalAgent(provider=provider, tool_executor_factory=lambda: executor)

    outputs = asyncio.run(_collect(agent, "Thanks, that was helpful."))

    assert executor.invocations == []
    assert provider.messages is not None, "answer model never ran"
    assert any("answering directly" in (output.content or "") for output in outputs)


async def _collect(agent: ChatTerminalAgent, message: str):
    return [output async for output in agent.stream(message=message, session=_session())]


async def _collect_with_session(agent: ChatTerminalAgent, message: str, session: TerminalSession):
    return [output async for output in agent.stream(message=message, session=session)]
