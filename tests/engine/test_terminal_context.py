import asyncio
from pathlib import Path

from engine.chat.effort import ChatEffort
from engine.cli.agents import ChatTerminalAgent
from engine.cli.context import ChatContextSelector
from engine.cli.models import TerminalContextFile, TerminalHistoryTurn, TerminalSession
from engine.llm.groq import GroqModel


class _FakeProvider:
    async def retrieve_model(self, *, api_key, model_id):
        return GroqModel(id=model_id, context_window=32_768, max_completion_tokens=2_000, active=True)

    async def stream_chat(self, *, api_key, config, messages):
        yield "done"


class _SummaryGenerator:
    async def summarize(self, *, previous_summary, turns, max_output_tokens):
        return "Durable local summary."


class _FailingSummaryGenerator:
    async def summarize(self, **kwargs):
        raise RuntimeError("summary unavailable")


def _session() -> TerminalSession:
    return TerminalSession(api_key="test", effort=ChatEffort.INSTANT)


def test_context_selector_caps_old_turns_and_document_chunks_by_effort() -> None:
    session = _session()
    session.history = [
        TerminalHistoryTurn(role="user", content=f"old unrelated {index}") for index in range(5)
    ] + [
        TerminalHistoryTurn(role="user", content="Modal worker execution uses trusted functions."),
        TerminalHistoryTurn(role="assistant", content="The worker is remote."),
    ]
    session.context_files = [
        TerminalContextFile(path=Path("a.md"), content="Modal functions execute trusted tool code."),
        TerminalContextFile(path=Path("b.md"), content="Unrelated text."),
    ]

    selection = ChatContextSelector().select(session=session, query="How does Modal execute tools?")

    assert len(selection.old_turns) <= 2
    assert len(selection.document_chunks) <= 3
    assert "Modal functions" in selection.context


def test_context_selector_reports_when_local_history_reaches_compaction_threshold() -> None:
    session = _session()
    session.history = [TerminalHistoryTurn(role="user", content="topic " * 2_500)]

    selection = ChatContextSelector().select(session=session, query="x")

    assert selection.compaction_required is True


def test_local_compaction_preserves_raw_history_and_prior_summary_on_failure() -> None:
    session = _session()
    session.history = [TerminalHistoryTurn(role="user", content="topic " * 2_500)]
    agent = ChatTerminalAgent(provider=_FakeProvider(), summary_generator=_SummaryGenerator())

    asyncio.run(_collect(agent, session))

    assert session.compacted_summary == "Durable local summary."
    assert session.compacted_through == len(session.history)
    immutable_length = len(session.history)

    session.history.append(TerminalHistoryTurn(role="user", content="new topic " * 2_500))
    failing_agent = ChatTerminalAgent(provider=_FakeProvider(), summary_generator=_FailingSummaryGenerator())
    outputs = asyncio.run(_collect(failing_agent, session))

    assert session.compacted_summary == "Durable local summary."
    assert session.compacted_through == immutable_length
    assert any("local summary retained" in output for output in outputs)


async def _collect(agent, session) -> list[str]:
    return [output.content async for output in agent.stream(message="summarize", session=session)]
