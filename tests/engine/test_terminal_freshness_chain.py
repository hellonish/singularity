import asyncio

from engine.chat.effort import ChatEffort
from engine.chat.modal_tools import ChatToolResult
from engine.cli.agents import ChatTerminalAgent, FreshnessEvidenceUnavailable
from engine.cli.models import TerminalSession
from engine.llm.groq import GroqModel


class CapturingProvider:
    def __init__(self) -> None:
        self.messages = None

    async def retrieve_model(self, *, api_key, model_id):
        return GroqModel(id=model_id, context_window=32_768, max_completion_tokens=2_000)

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

    assert [call.tool_name for call in executor.invocations] == ["web_search"]
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


async def _collect(agent: ChatTerminalAgent, message: str):
    return [output async for output in agent.stream(message=message, session=_session())]
