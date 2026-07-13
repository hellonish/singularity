import asyncio

from engine.chat.effort import ChatEffort
from engine.cli.models import TerminalSession
from engine.cli.repl import EngineREPL
from engine.cli.settings import TerminalSettings


class FakeSettingsStore:
    def __init__(self) -> None:
        self.settings = TerminalSettings()

    def load(self):
        return self.settings

    def save(self, settings):
        self.settings = settings


def test_effort_command_uses_interactive_selection(capsys) -> None:
    repl = EngineREPL(TerminalSession(api_key="test"), settings_store=FakeSettingsStore())

    async def choose(**kwargs):
        return ChatEffort.ULTRA

    repl.ui.choose = choose
    asyncio.run(repl._choose_effort())

    assert repl.session.effort is ChatEffort.ULTRA
    assert repl.session.max_output_tokens == 3_000
    assert "timeout=420s" in capsys.readouterr().out


def test_cancelled_effort_selection_preserves_current_effort() -> None:
    repl = EngineREPL(TerminalSession(api_key="test"), settings_store=FakeSettingsStore())

    async def choose(**kwargs):
        return None

    repl.ui.choose = choose
    asyncio.run(repl._choose_effort())

    assert repl.session.effort is ChatEffort.MEDIUM


def test_effort_command_shows_research_depths_in_research_mode(capsys) -> None:
    repl = EngineREPL(
        TerminalSession(api_key="test", agent_name="research"),
        settings_store=FakeSettingsStore(),
    )
    selection = {}

    async def choose(**kwargs):
        selection.update(kwargs)
        return ChatEffort.HIGH

    repl.ui.choose = choose
    asyncio.run(repl._choose_effort())

    assert selection["title"] == "Select research depth"
    assert [value for value, _ in selection["values"]] == [
        ChatEffort.INSTANT,
        ChatEffort.MEDIUM,
        ChatEffort.HIGH,
    ]
    assert "Quick" in selection["values"][0][1]
    assert "6 nodes" in selection["values"][0][1]
    assert "6m per model step" in selection["values"][0][1]
    assert "20m run max" in selection["values"][0][1]
    assert "Standard" in selection["values"][1][1]
    assert "8 nodes" in selection["values"][1][1]
    assert "7m 30s per model step" in selection["values"][1][1]
    assert "30m run max" in selection["values"][1][1]
    assert "Deep" in selection["values"][2][1]
    assert "12 nodes" in selection["values"][2][1]
    assert "10m per model step" in selection["values"][2][1]
    assert "60m run max" in selection["values"][2][1]
    assert repl.session.effort is ChatEffort.HIGH
    assert "Research depth selected: deep" in capsys.readouterr().out


def test_research_depth_maps_saved_ultra_to_deep_default() -> None:
    repl = EngineREPL(
        TerminalSession(api_key="test", agent_name="research", effort=ChatEffort.ULTRA),
        settings_store=FakeSettingsStore(),
    )
    selection = {}

    async def choose(**kwargs):
        selection.update(kwargs)
        return None

    repl.ui.choose = choose
    asyncio.run(repl._choose_effort())

    assert selection["default"] is ChatEffort.HIGH
    assert repl.session.effort is ChatEffort.ULTRA
