"""Prompt-toolkit input and Rich output primitives for the terminal client."""
from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import DummyHistory, InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Box, Frame, RadioList
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text

COMMAND_WORDS = (
    "/help", "/provider", "/models", "/effort", "/mode", "/key", "/status", "/reset", "/clear", "/quit",
)


def _highlighted_value(choices: RadioList):
    """Return the row under the cursor, not the previously checked row."""
    return choices.values[choices._selected_index][0]


class TerminalUI:
    """Single owner for rendering and interactive, multiline terminal input."""

    def __init__(self, *, session_state: Callable[[], dict[str, str]], console: Console | None = None) -> None:
        self.console = console or Console()
        self._session_state = session_state
        self._status: Status | None = None
        self._live_answer: Live | None = None
        self._live_answer_content = ""
        self._prompt = PromptSession(
            history=InMemoryHistory(),
            multiline=True,
            completer=WordCompleter(COMMAND_WORDS, sentence=True),
            complete_while_typing=True,
            key_bindings=self._key_bindings(),
            style=Style.from_dict({
                "prompt": "bold cyan",
                "bottom-toolbar": "bg:#1f2937 #d1d5db",
            }),
        )

    def _key_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add("enter")
        def _submit(event) -> None:
            event.current_buffer.validate_and_handle()

        # Most terminal emulators encode Shift+Enter as Escape followed by
        # Enter; prompt_toolkit represents that as this two-key sequence.
        @bindings.add("escape", "enter")
        def _newline(event) -> None:
            event.current_buffer.insert_text("\n")

        @bindings.add("c-c")
        def _clear_then_cancel(event) -> None:
            if event.current_buffer.text:
                event.current_buffer.reset()
                return
            event.app.exit(exception=KeyboardInterrupt)

        return bindings

    async def prompt(self) -> str:
        state = self._session_state()
        return await self._prompt.prompt_async(
            HTML(f"<prompt>╭─ singularity[{state['agent']}]</prompt>\n<prompt>╰─› </prompt>"),
            bottom_toolbar=lambda: (
                f" agent={self._session_state()['agent']}  model={self._session_state()['model']}  "
                f"effort={self._session_state()['effort']}  key={self._session_state()['key']}  "
                "Enter send · Shift+Enter newline · Tab complete"
            ),
            prompt_continuation="   · ",
        )

    def banner(self, *, logo: str, agent: str, model: str, effort: str, key_configured: bool, modal_enabled: bool, api_backed: bool = False, provider: str = "Groq") -> None:
        self.console.print(logo, style="bold cyan")
        details = Table.grid(padding=(0, 2))
        details.add_row("Agent", agent, "Model", model)
        details.add_row("Effort", effort, f"{provider} key", "configured" if key_configured else "not configured")
        tools = "Server managed" if api_backed else ("Modal enabled" if modal_enabled else "Local chat only")
        details.add_row("Tools", tools, "Input", "Enter send · Shift+Enter newline")
        self.console.print(
            Panel(
                details,
                title="Singularity Chat · interactive terminal agent runtime",
                border_style="cyan",
                expand=False,
            )
        )

    def help(self, commands: list[tuple[str, str]]) -> None:
        hosted = self._session_state().get("backend") == "api"
        runtime = (
            "a streaming client for the hosted Singularity API"
            if hosted
            else "a local streaming AI runtime"
        )
        persistence = (
            "The API persists chats and research reports; /reset starts a fresh chat in this process."
            if hosted
            else "Conversation history is discarded when the process exits or when /reset is used."
        )
        self.console.print(Panel(
            f"[bold]Singularity[/bold] is {runtime}, backed by Groq, DeepSeek, or OpenRouter. "
            "It stores provider keys and renewable CLI session state in a private global configuration file. "
            f"{persistence}\n\n"
            "Type a message and press Enter to send. Use Shift+Enter for a new line. Commands beginning with / "
            "control the current session. Model and effort choices use arrow keys and Enter.",
            title="About Singularity",
            border_style="cyan",
        ))
        table = Table(title="Commands", border_style="cyan")
        table.add_column("Command", style="bold cyan", no_wrap=True)
        table.add_column("Description")
        for command, description in commands:
            table.add_row(command, description)
        self.console.print(table)

    async def choose(self, *, title: str, text: str, values, default=None):
        return await self._inline_selector(title=title, text=text, values=values, default=default).run_async()

    @staticmethod
    def _inline_selector(*, title: str, text: str, values, default=None) -> Application:
        """Build an inline list that never enters the terminal alternate screen."""
        choices = RadioList(
            values=values,
            default=default,
            open_character=" ",
            select_character="›",
            close_character=" ",
            show_scrollbar=True,
            select_on_focus=True,
        )
        bindings = KeyBindings()

        @bindings.add("enter", eager=True)
        def _accept(event) -> None:
            event.app.exit(result=_highlighted_value(choices))

        @bindings.add("escape", eager=True)
        @bindings.add("c-c", eager=True)
        def _cancel(event) -> None:
            event.app.exit(result=None)

        visible_rows = min(max(len(values), 2), 10)
        body = HSplit([
            Window(FormattedTextControl(text), height=1, style="class:selector-help"),
            Box(Frame(choices, title=title), height=Dimension.exact(visible_rows + 2)),
            Window(
                FormattedTextControl("↑/↓ move  ·  Enter select  ·  Esc cancel"),
                height=1,
                style="class:selector-help",
            ),
        ])
        return Application(
            layout=Layout(body, focused_element=choices),
            key_bindings=bindings,
            full_screen=False,
            erase_when_done=True,
            mouse_support=False,
            style=Style.from_dict({
                "frame.border": "#06b6d4",
                "frame.label": "bold #22d3ee",
                "radio-selected": "bold #22d3ee",
                "radio-checked": "bold #22c55e",
                "selector-help": "#94a3b8",
            }),
        )

    async def prompt_secret(self, message: str) -> str:
        # Use a disposable prompt so a credential never enters chat history.
        # ``erase_when_done`` also removes the masked stars from scrollback.
        secret_prompt = PromptSession(
            history=DummyHistory(),
            multiline=False,
            is_password=True,
            erase_when_done=True,
            style=Style.from_dict({
                "prompt": "bold cyan",
                "bottom-toolbar": "bg:#1f2937 #d1d5db",
            }),
        )
        return await secret_prompt.prompt_async(
            HTML(f"<prompt>{message}</prompt>"),
            bottom_toolbar="Input is hidden · Enter save · Ctrl+C cancel",
        )

    def table(self, *, title: str, rows: list[tuple[str, str]]) -> None:
        table = Table(title=title, border_style="cyan")
        table.add_column("Setting", style="bold cyan")
        table.add_column("Value")
        for key, value in rows:
            table.add_row(key, value)
        self.console.print(table)

    def info(self, message: str) -> None:
        self.console.print(f"[cyan]•[/cyan] {message}")

    def warning(self, message: str) -> None:
        self.console.print(f"[yellow]⚠[/yellow] {message}")

    def error(self, message: str) -> None:
        self.console.print(Panel(message, title="Error", border_style="red"))

    def answer(self, content: str) -> None:
        """Render a complete, non-streamed answer such as a research report."""
        self.console.print(Panel(Markdown(content), title="Answer", border_style="green"))

    def start_status(self, message: str) -> None:
        self.stop_status()
        self._status = self.console.status(message, spinner="dots")
        self._status.start()

    def update_status(self, message: str) -> None:
        if self._status is None:
            self.start_status(message)
        else:
            self._status.update(message)

    def stop_status(self) -> None:
        if self._status is not None:
            self._status.stop()
            self._status = None

    def stream_delta(self, text: str) -> None:
        if not self.console.is_terminal or self.console.no_color:
            self.console.print(text, end="", markup=False, highlight=False)
            return
        self._live_answer_content += text
        renderable = Panel(
            Markdown(self._live_answer_content),
            title="Answer",
            border_style="green",
        )
        if self._live_answer is None:
            self._live_answer = Live(
                renderable,
                console=self.console,
                refresh_per_second=12,
                transient=False,
                vertical_overflow="ellipsis",
            )
            self._live_answer.start(refresh=True)
        else:
            self._live_answer.update(renderable, refresh=True)

    def final_answer(self, content: str) -> None:
        if self._live_answer is not None:
            self._live_answer.update(
                Panel(Markdown(content), title="Answer", border_style="green"),
                refresh=True,
            )
            self._live_answer.stop()
            self._live_answer = None
            self._live_answer_content = ""
        elif not self.console.is_terminal or self.console.no_color:
            self.console.print()
        elif content:
            # Defensive fallback for providers that complete without deltas.
            self.console.print(Panel(Markdown(content), title="Answer", border_style="green"))

    def model_rows(self, models, selected_model: str) -> list[tuple[str, str]]:
        return [(model.id, "selected" if model.id == selected_model else "available") for model in models]

    def render_lifecycle(self, *, kind: str, content: str, elapsed_seconds: float | None = None) -> None:
        if kind == "thinking":
            self.start_status("Thinking…")
        elif kind == "tool_planning_start":
            self.update_status(content + "…")
        elif kind == "tool_planning_timeout":
            self.stop_status()
            self.warning(content)
        elif kind == "tool_start":
            self.update_status(f"Using {content}…")
        elif kind == "tool_completed":
            self.stop_status()
            suffix = f" in {elapsed_seconds:.1f}s" if elapsed_seconds is not None else ""
            self.info(f"Completed {content}{suffix}")
        elif kind == "tool_failed":
            self.stop_status()
            self.warning(f"Tool unavailable: {content}")
        elif kind == "model_started":
            self.update_status("Thinking…")
        elif kind == "metadata":
            self.info(content)
        elif kind == "completed":
            self.stop_status()

    def render_research_progress(self, event: dict) -> None:
        """Render bounded-research progress without exposing tool payloads."""
        status = str(event.get("status", ""))
        message = str(event.get("message", "Research progress"))
        elapsed = event.get("elapsed_seconds")
        if status in {"started", "node_started", "tool_dispatched"}:
            self.update_status(message + "…")
            return
        if status == "tool_completed":
            suffix = f" in {float(elapsed):.1f}s" if isinstance(elapsed, (int, float)) else ""
            sources = event.get("source_count")
            source_text = f" — {sources} source(s)" if isinstance(sources, int) else ""
            self.info(f"{message}{source_text}{suffix}")
            return
        if status == "tool_failed":
            self.warning(message)
            return
        if status == "skipped":
            self.warning(message)
            return
        if status in {"completed", "node_completed"}:
            self.info(message)
