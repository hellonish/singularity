"""
Interactive REPL for the Singularity Chat Agent.

Run from project root:

    python -m agents.chat.cli
    python -m agents.chat.cli --extended
    python -m agents.chat.cli --model grok-3

Commands (type during chat session):
    /model                — show current model + available models
    /model <id>           — switch to a different model (e.g. /model gemini-2.5-pro-preview-03-25)
    /mode chat            — force chat mode for all messages
    /mode research        — force research mode for all messages
    /mode auto            — let the thinker decide (default)
    /extended on|off      — toggle extended thinking
    /clear                — clear conversation history
    /history              — show conversation history
    /skills               — list all 44 available skills
    /quit  or /exit       — exit

Inline message flags:
    --research            — override mode to research for this message
    --extended            — override extended thinking on for this message
    --audience <a>        — override audience (layperson/student/practitioner/expert/executive)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import textwrap
from pathlib import Path

# Ensure project root on sys.path before any local imports
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv()

# Initialize skill registry at startup
from skills import _register_real_skills
_register_real_skills()

logging.basicConfig(level=logging.WARNING, format="%(message)s")

from agents.chat.agent import ChatAgent
from agents.chat.thinker import ThinkPlan
from agents.chat.models import AVAILABLE_MODELS, DEFAULT_MODEL_ID, get_model_info
from skills import SKILL_DOCS


# ---------------------------------------------------------------------------
# ANSI color helpers
# ---------------------------------------------------------------------------

def _supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

_COLOR = _supports_color()

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text

def cyan(t: str)    -> str: return _c(t, "96")
def green(t: str)   -> str: return _c(t, "92")
def yellow(t: str)  -> str: return _c(t, "93")
def magenta(t: str) -> str: return _c(t, "95")
def bold(t: str)    -> str: return _c(t, "1")
def dim(t: str)     -> str: return _c(t, "2")
def red(t: str)     -> str: return _c(t, "91")
def blue(t: str)    -> str: return _c(t, "94")


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = """
  ╔══════════════════════════════════════════════════════════════╗
  ║                                                              ║
  ║    ███████╗██╗███╗   ██╗ ██████╗ ██╗   ██╗██╗      █████╗  ║
  ║    ██╔════╝██║████╗  ██║██╔════╝ ██║   ██║██║     ██╔══██╗ ║
  ║    ███████╗██║██╔██╗ ██║██║  ███╗██║   ██║██║     ███████║ ║
  ║    ╚════██║██║██║╚██╗██║██║   ██║██║   ██║██║     ██╔══██║ ║
  ║    ███████║██║██║ ╚████║╚██████╔╝╚██████╔╝███████╗██║  ██║ ║
  ║    ╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝ ║
  ║                                                              ║
  ║          Dual-Mode AI Research Agent                         ║
  ╚══════════════════════════════════════════════════════════════╝
"""

def _print_banner(extended: bool, model_id: str) -> None:
    print(cyan(BANNER))
    info = get_model_info(model_id)
    model_label = info.display_name if info else model_id
    provider = info.provider.upper() if info else ""
    mode_str = yellow("EXTENDED") if extended else green("STANDARD")
    print(f"  Model         : {bold(model_label)}  {dim(f'[{provider}]')}")
    print(f"  Thinking mode : {mode_str}")
    print(f"  Commands      : {dim('/model  /mode chat|research|auto  /extended on|off  /skills  /quit')}")
    print()


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _render_plan(plan: ThinkPlan) -> None:
    """Pretty-print the ThinkPlan before execution."""
    mode_label = (
        red("◉ RESEARCH MODE") if plan.mode == "research"
        else green("◎ CHAT MODE")
    )
    print(f"\n  {'─'*58}")
    print(f"  {bold('Thinking...')}  {mode_label}")
    print(f"  {'─'*58}")
    print(f"  {dim('Reasoning:')} {plan.reasoning}")

    if plan.selected_skills:
        skills_str = "  ".join(f"`{s}`" for s in plan.selected_skills)
        print(f"  {dim('Skills   :')} {skills_str}")

    print(f"\n  {bold('Step Plan:')}")

    STEP_ICONS = {
        "direct_answer": "💬",
        "web_search":    "🌐",
        "skill_call":    "🔧",
        "analyze":       "🔍",
        "summarize":     "📝",
        "identity":      "✨",
    }

    for step in plan.steps:
        icon = STEP_ICONS.get(step.type, "•")
        skill_tag = f" {dim('[' + step.skill_name + ']')}" if step.skill_name else ""
        desc = textwrap.shorten(step.description, width=62)
        print(f"    {dim(str(step.step_id) + '.')} {icon} {cyan(step.type)}{skill_tag}  {dim(desc)}")

    print(f"  {'─'*58}\n")


def _render_step_header(step_id: int, step_type: str, description: str) -> None:
    STEP_ICONS = {
        "direct_answer": "💬",
        "web_search":    "🌐",
        "skill_call":    "🔧",
        "analyze":       "🔍",
        "summarize":     "📝",
        "identity":      "✨",
    }
    icon = STEP_ICONS.get(step_type, "•")
    desc = textwrap.shorten(description, width=55)
    print(f"\n  {dim(f'[Step {step_id}]')} {icon} {cyan(step_type)}  {dim(desc)}")
    print(f"  {'·'*58}")


def _render_model_list(current_model_id: str) -> None:
    """Render the model selection table."""
    print(f"\n  {bold('Available Models:')}\n")
    
    by_provider: dict[str, list] = {}
    for m in AVAILABLE_MODELS:
        by_provider.setdefault(m.provider, []).append(m)

    provider_order = ["grok", "gemini", "deepseek"]
    provider_labels = {
        "grok": "  ⚡ xAI — Grok",
        "gemini": "  🔮 Google — Gemini",
        "deepseek": "  🐋 DeepSeek",
    }

    for provider in provider_order:
        models = by_provider.get(provider, [])
        if not models:
            continue
        print(f"  {bold(provider_labels[provider])}")
        for m in models:
            active = green(" ◀ active") if m.model_id == current_model_id else ""
            tags = dim(f"  [{', '.join(m.tags)}]") if m.tags else ""
            print(f"    {cyan(m.model_id):<45} {m.display_name}{tags}{active}")
            print(f"    {dim(' ' * 45 + m.description)}")
        print()

    print(f"  {dim('Usage: /model <model_id>   e.g. /model gemini-2.5-pro-preview-03-25')}")
    print()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

class Session:
    def __init__(self, extended: bool, model_id: str) -> None:
        self.extended     = extended
        self.model_id     = model_id
        self.mode_force: str | None = None   # None=auto, "chat", "research"
        self.history: list[dict[str, str]] = []
        self.turn_count   = 0

    def add(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        if len(self.history) > 10:
            self.history = self.history[-10:]


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _handle_command(cmd: str, session: Session, agent: ChatAgent) -> bool:
    """Returns True if the input was a command."""
    parts = cmd.strip().split()
    if not parts:
        return False
    head = parts[0].lower()

    if head in ("/quit", "/exit"):
        print(cyan("\n  Goodbye! ✨\n"))
        sys.exit(0)

    elif head == "/clear":
        session.history.clear()
        print(green("  ✓ Conversation history cleared.\n"))
        return True

    elif head == "/history":
        if not session.history:
            print(dim("  (no history)\n"))
        else:
            print()
            for turn in session.history:
                label = bold("You") if turn["role"] == "user" else bold("Singularity")
                preview = turn["content"][:150]
                print(f"  {label}: {preview}")
            print()
        return True

    elif head == "/skills":
        # Skill menu is sourced live from skill.md via SkillDocs.
        skill_lines = [line for line in SKILL_DOCS.thinker_menu().splitlines() if line.strip()]
        skill_rows = [line for line in skill_lines if not line.startswith("Tier ")]
        print(f"\n  {bold('Available Skills')} ({len(skill_rows)}):\n")
        for line in skill_lines:
            if line.startswith("Tier "):
                print(f"  {bold(line)}")
            else:
                print(f"    {dim(line.strip())}")
        print()
        return True

    elif head == "/model":
        if len(parts) < 2:
            # Show model list
            _render_model_list(session.model_id)
            return True
        # Switch model
        new_model_id = parts[1]
        # Validate
        all_ids = [m.model_id for m in AVAILABLE_MODELS]
        if new_model_id not in all_ids:
            print(red(f"\n  Unknown model '{new_model_id}'.\n"))
            print(f"  {dim('Available:')} {dim(', '.join(all_ids))}\n")
            return True
        try:
            agent.set_model(new_model_id)
            session.model_id = new_model_id
            info = get_model_info(new_model_id)
            label = info.display_name if info else new_model_id
            print(green(f"\n  ✓ Switched to {bold(label)}  [{new_model_id}]\n"))
        except Exception as exc:
            print(red(f"\n  Failed to switch model: {exc}\n"))
        return True

    elif head == "/mode":
        if len(parts) < 2:
            current = session.mode_force or "auto"
            print(f"  Current mode override: {yellow(current)}\n")
            return True
        val = parts[1].lower()
        if val in ("chat", "research", "auto"):
            session.mode_force = None if val == "auto" else val
            print(green(f"  ✓ Mode override set to: {val}\n"))
        else:
            print(red(f"  Unknown mode '{val}'. Use: chat | research | auto\n"))
        return True

    elif head == "/extended":
        if len(parts) < 2:
            print(f"  Extended thinking: {yellow('on' if session.extended else 'off')}\n")
            return True
        val = parts[1].lower()
        if val == "on":
            session.extended = True
            agent.extended = True
            print(green("  ✓ Extended thinking ON\n"))
        elif val == "off":
            session.extended = False
            agent.extended = False
            print(green("  ✓ Extended thinking OFF\n"))
        else:
            print(red(f"  Unknown value '{val}'. Use: on | off\n"))
        return True

    return False


# ---------------------------------------------------------------------------
# Inline flag parser
# ---------------------------------------------------------------------------

def _parse_inline_flags(message: str) -> tuple[str, dict]:
    """
    Strip inline flags from the message → (clean_message, overrides).
    Flags: --research, --extended, --audience <value>
    """
    overrides: dict = {}
    words = message.split()
    clean_words = []
    i = 0
    while i < len(words):
        w = words[i]
        if w == "--research":
            overrides["mode"] = "research"
        elif w == "--extended":
            overrides["extended"] = True
        elif w == "--audience" and i + 1 < len(words):
            overrides["audience"] = words[i + 1]
            i += 1
        else:
            clean_words.append(w)
        i += 1
    return " ".join(clean_words), overrides


# ---------------------------------------------------------------------------
# Main chat turn
# ---------------------------------------------------------------------------

async def _run_chat_turn(
    agent: ChatAgent,
    message: str,
    session: Session,
    mode_override: str | None,
) -> str:
    """Execute one chat turn. Returns the full assistant response."""

    plan = await asyncio.to_thread(agent.think, message, session.history)

    # Apply mode override
    effective_mode = mode_override or session.mode_force or plan.mode
    plan.mode = effective_mode

    _render_plan(plan)

    full_response_parts: list[str] = []

    if plan.mode == "research":
        print(f"  {yellow('◉ Starting research pipeline — this may take 1-3 minutes...')}\n")
        import logging as _logging
        _logging.getLogger().setLevel(_logging.INFO)
        report = await agent.run_research_mode(plan, message)
        _logging.getLogger().setLevel(_logging.WARNING)
        print(f"\n{report}\n")
        full_response_parts.append(report)

    else:
        print(f"  {dim('Response:')}\n")
        non_trivial_plan = (
            len(plan.steps) > 1 or
            (plan.steps and plan.steps[0].type not in ("direct_answer", "identity"))
        )

        async for chunk in agent.run_chat_mode(plan, message, session.history):
            if chunk.startswith("§STEP:"):
                _, sid, stype, sdesc = chunk.rstrip("\n").split(":", 3)
                if non_trivial_plan:
                    _render_step_header(int(sid), stype, sdesc)
            else:
                print(chunk, end="", flush=True)
                full_response_parts.append(chunk)

        print()  # newline after streaming

    return "".join(full_response_parts)


# ---------------------------------------------------------------------------
# REPL main loop
# ---------------------------------------------------------------------------

async def main(extended: bool = False, model_id: str = DEFAULT_MODEL_ID) -> None:
    session = Session(extended=extended, model_id=model_id)
    agent   = ChatAgent(model_id=model_id, extended=extended)

    _print_banner(extended, model_id)

    while True:
        try:
            # Current model tag in prompt
            info = get_model_info(session.model_id)
            model_short = (info.display_name if info else session.model_id).split()[0]
            prompt_label = f"{cyan('You')} {dim('[' + model_short + ']')} › "

            try:
                raw = input(f"\n{prompt_label}").strip()
            except (EOFError, KeyboardInterrupt):
                print(cyan("\n\n  Goodbye! ✨\n"))
                break

            if not raw:
                continue

            # Commands
            if raw.startswith("/"):
                if _handle_command(raw, session, agent):
                    continue

            # Inline flags
            message, overrides = _parse_inline_flags(raw)
            if not message:
                continue

            effective_extended = overrides.get("extended", session.extended)
            agent.extended = effective_extended
            mode_override = overrides.get("mode")

            session.add("user", message)
            session.turn_count += 1

            try:
                response = await _run_chat_turn(
                    agent=agent,
                    message=message,
                    session=session,
                    mode_override=mode_override,
                )
                session.add("assistant", response)
            except Exception as exc:
                print(red(f"\n  [Error] {exc}\n"))
                import traceback
                traceback.print_exc()

        except KeyboardInterrupt:
            print(cyan("\n\n  (Interrupted — type /quit to exit)\n"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Singularity — Dual-Mode AI Research Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python -m agents.chat.cli
              python -m agents.chat.cli --extended
              python -m agents.chat.cli --model gemini-2.5-pro-preview-03-25

            In-session commands:
              /model                     List all available models
              /model grok-3              Switch to Grok 3
              /mode research             Force research mode
              /extended on               Enable extended thinking
              /skills                    List all 44 skills
              /clear                     Reset conversation history
              /quit                      Exit
        """),
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        default=False,
        help="Enable extended thinking (allows 5-10 step plans, research mode)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_ID,
        help=f"Response model ID (default: {DEFAULT_MODEL_ID})",
    )
    args = parser.parse_args()
    asyncio.run(main(extended=args.extended, model_id=args.model))
