from io import StringIO

from rich.console import Console

from engine.chat.modal_tools import ChatToolResult
from engine.chat.runtime import format_tool_context
from engine.chat.tool_loop import ExecutedToolCall
from engine.cli.ui import TerminalUI, _highlighted_value
from prompt_toolkit.widgets import RadioList


def _ui() -> tuple[TerminalUI, Console]:
    console = Console(record=True, force_terminal=True, width=120)
    return (
        TerminalUI(
            session_state=lambda: {"agent": "chat", "model": "test", "effort": "medium", "key": "saved"},
            console=console,
        ),
        console,
    )


def test_rich_ui_renders_dashboard_tables_and_styled_errors() -> None:
    ui, console = _ui()
    ui.banner(logo="LOGO", agent="chat", model="test", effort="medium", key_configured=False, modal_enabled=False)
    ui.table(title="Session status", rows=[("Agent", "chat")])
    ui.error("bad input")

    rendered = console.export_text()
    assert "Singularity Chat" in rendered
    assert "Session status" in rendered
    assert "bad input" in rendered


def test_selector_is_inline_and_erases_only_its_component() -> None:
    application = TerminalUI._inline_selector(
        title="Effort",
        text="Choose one",
        values=[("instant", "Instant"), ("medium", "Medium")],
        default="medium",
    )

    assert application.full_screen is False
    assert application.erase_when_done is True


def test_selector_commits_highlighted_row_instead_of_previous_default() -> None:
    choices = RadioList([("first", "First"), ("second", "Second")], default="first")
    choices._selected_index = 1

    assert choices.current_value == "first"
    assert _highlighted_value(choices) == "second"


def test_redirected_answer_stream_is_emitted_once_without_final_duplicate() -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False, no_color=True)
    ui = TerminalUI(
        session_state=lambda: {"agent": "chat", "model": "test", "effort": "medium", "key": "saved"},
        console=console,
    )

    ui.stream_delta("An **AML")
    ui.stream_delta(" system**")
    ui.final_answer("An **AML system**")

    assert output.getvalue().count("An **AML system**") == 1


def test_tool_context_includes_bounded_source_references() -> None:
    calls = (
        ExecutedToolCall(
            skill_id="medical_research",
            tool_name="pubmed",
            result=ChatToolResult(
                content="Study result",
                sources=[
                    {"title": "Study A", "url": "https://example.test/a", "credibility_base": 0.9},
                    {"title": "Study B", "url": "https://example.test/b", "credibility_base": 0.8},
                ],
                credibility_base=0.8,
                error=None,
            ),
        ),
    )

    context = format_tool_context(calls, max_citations=1)

    assert "Study result" in context
    assert "Study A" in context
    assert "Study B" not in context
    assert "credibility=0.9" in context


def test_tool_lifecycle_shows_the_actual_validated_call() -> None:
    ui, console = _ui()

    ui.render_lifecycle(
        kind="tool_completed",
        content='web_search(query="new grad SWE", arguments={"max_results": 8}) — 8 source(s)',
        elapsed_seconds=0.4,
    )

    rendered = console.export_text()
    assert "web_search(query" in rendered
    assert "8 source(s)" in " ".join(rendered.split())
