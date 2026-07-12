import asyncio

from engine.chat.effort import ChatEffort
from engine.cli.models import TerminalSession
from engine.cli.repl import EngineREPL


def test_effort_command_uses_interactive_selection(capsys) -> None:
    repl = EngineREPL(TerminalSession(api_key="test"))

    async def choose(**kwargs):
        return ChatEffort.ULTRA

    repl.ui.choose = choose
    asyncio.run(repl._choose_effort())

    assert repl.session.effort is ChatEffort.ULTRA
    assert repl.session.max_output_tokens == 6_000
    assert "timeout=420s" in capsys.readouterr().out


def test_cancelled_effort_selection_preserves_current_effort() -> None:
    repl = EngineREPL(TerminalSession(api_key="test"))

    async def choose(**kwargs):
        return None

    repl.ui.choose = choose
    asyncio.run(repl._choose_effort())

    assert repl.session.effort is ChatEffort.MEDIUM
