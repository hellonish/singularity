from __future__ import annotations

from collections.abc import Iterable


LOGO = r"""
███████╗██╗███╗   ██╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ ██╗████████╗██╗   ██╗
██╔════╝██║████╗  ██║██╔════╝ ██║   ██║██║     ██╔══██╗██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝
███████╗██║██╔██╗ ██║██║  ███╗██║   ██║██║     ███████║██████╔╝██║   ██║    ╚████╔╝
╚════██║██║██║╚██╗██║██║   ██║██║   ██║██║     ██╔══██║██╔══██╗██║   ██║     ╚██╔╝
███████║██║██║ ╚████║╚██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║██║   ██║      ██║
╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝
""".strip("\n")
BANNER = LOGO


COMMANDS = (
    ("/help", "About Singularity, usage, privacy, and command reference"),
    ("/provider", "Choose Groq, DeepSeek, or OpenRouter with arrow keys"),
    ("/models", "Choose a model for the selected provider"),
    ("/effort", "Choose chat effort or bounded research depth"),
    ("/mode", "Choose chat or bounded research mode with arrow keys"),
    ("/key", "Set, inspect, or remove the selected provider API key"),
    ("/status", "Show the current model, effort, credentials, tools, and session state"),
    ("/reset", "Clear this ephemeral conversation history"),
    ("/clear", "Clear the terminal screen"),
    ("/quit", "Exit Singularity"),
)


def _box(
    lines: Iterable[str],
    *,
    title: str | None = None,
    width: int,
) -> str:
    """Render a fixed-width ASCII box."""

    inner_width = width - 4
    output: list[str] = []

    if title:
        label = f" {title} "
        remaining = width - len(label) - 2
        output.append("+" + label + "-" * remaining + "+")
    else:
        output.append("+" + "-" * (width - 2) + "+")

    for line in lines:
        if len(line) > inner_width:
            line = line[: inner_width - 3] + "..."

        output.append(f"|  {line:<{inner_width}}|")

    output.append("+" + "-" * (width - 2) + "+")
    return "\n".join(output)


def _command_lines() -> list[str]:
    command_width = max(len(command) for command, _ in COMMANDS)

    return [
        f"{command:<{command_width}}  {description}"
        for command, description in COMMANDS
    ]


def render_banner(
    *,
    version: str = "engine v2",
    agent: str = "chat",
    model: str | None = None,
    effort: str = "medium",
) -> str:
    logo_lines = LOGO.splitlines()

    # The logo currently requires roughly 91 terminal columns.
    width = max(
        94,
        max(len(line) for line in logo_lines) + 4,
    )

    model_name = model or "not selected"

    introduction = [
        "Agentic research and terminal agent runtime.",
        "",
        f"Version : {version}",
        f"Agent   : {agent}",
        f"Model   : {model_name}",
        f"Effort  : {effort}",
        "",
        "Enter plain text to chat, or use one of the commands below.",
    ]

    return "\n\n".join(
        [
            _box(logo_lines, width=width),
            _box(
                introduction,
                title="SINGULARITY TERMINAL",
                width=width,
            ),
            _box(
                _command_lines(),
                title="COMMANDS",
                width=width,
            ),
            "  Ready. Type /help for detailed usage.",
        ]
    )
