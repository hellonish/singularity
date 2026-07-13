import asyncio

from engine.cli.models import TerminalSession
from engine.cli.repl import EngineREPL


def test_mode_selector_routes_plain_text_to_live_research_with_a_groq_key() -> None:
    repl = EngineREPL(TerminalSession(api_key="saved-key"))

    async def choose(**kwargs):
        assert kwargs["title"] == "Select mode"
        return "research"

    calls: list[str] = []

    async def run_research(query: str) -> None:
        calls.append(query)

    repl.ui.choose = choose
    repl._research_live = run_research  # type: ignore[method-assign]

    asyncio.run(repl._choose_mode())
    asyncio.run(repl._send("How does bounded research work?"))

    assert repl.session.agent_name == "research"
    assert calls == ["How does bounded research work?"]
