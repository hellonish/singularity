from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone

from engine.chat.prompt import CHAT_SYSTEM_PROMPT_PATH, build_runtime_system_prompt, load_chat_system_prompt
from engine.cli.banner import BANNER, render_banner


def test_banner_and_chat_prompt_are_standalone_assets() -> None:
    assert "Singularity" not in BANNER  # ASCII artwork remains independently renderable.
    assert "terminal agent runtime" in render_banner()
    assert CHAT_SYSTEM_PROMPT_PATH.name == "system.md"
    assert CHAT_SYSTEM_PROMPT_PATH.is_file()
    assert "You are Singularity" in load_chat_system_prompt()


def test_runtime_prompt_injects_server_generated_current_time() -> None:
    prompt = build_runtime_system_prompt(now=datetime(2026, 7, 12, 20, 30, tzinfo=timezone.utc))

    assert "2026-07-12T20:30:00+00:00" in prompt
    assert "timezone=UTC" in prompt
    assert "Model knowledge may be outdated" in prompt


def test_terminal_repl_starts_and_handles_commands_as_a_real_process() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "engine.cli"],
        input="/status\n/help\n/quit\n",
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "terminal agent runtime" in result.stdout
    assert "Session status" in result.stdout
    assert "About Singularity" in result.stdout
    assert "/mode" in result.stdout
    assert "Model" in result.stdout
