from __future__ import annotations

from functools import lru_cache
from pathlib import Path

CHAT_SYSTEM_PROMPT_PATH = Path(__file__).with_name("prompts") / "system.md"


@lru_cache(maxsize=1)
def load_chat_system_prompt() -> str:
    prompt = CHAT_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not prompt:
        raise RuntimeError(f"Chat system prompt is empty: {CHAT_SYSTEM_PROMPT_PATH}")
    return prompt
