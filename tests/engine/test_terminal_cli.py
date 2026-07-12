from __future__ import annotations

import subprocess
import sys

from engine.chat.prompt import CHAT_SYSTEM_PROMPT_PATH, load_chat_system_prompt
from engine.cli.banner import BANNER, render_banner


def test_banner_and_chat_prompt_are_standalone_assets() -> None:
    assert "Singularity" not in BANNER  # ASCII artwork remains independently renderable.
    assert "terminal agent runtime" in render_banner()
    assert CHAT_SYSTEM_PROMPT_PATH.name == "system.md"
    assert CHAT_SYSTEM_PROMPT_PATH.is_file()
    assert "Singularity chat agent" in load_chat_system_prompt()


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
    assert "openai/gpt-oss-20b" in result.stdout
