from rich.console import Console

from engine.cli.ui import TerminalUI


def test_complete_research_report_is_rendered_as_an_answer() -> None:
    console = Console(record=True, width=100)
    ui = TerminalUI(session_state=lambda: {}, console=console)

    ui.answer("# Finding\n\nThe report is shown in chat.")

    output = console.export_text()
    assert "Answer" in output
    assert "Finding" in output
    assert "The report is shown in chat." in output
