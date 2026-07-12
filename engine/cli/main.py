from __future__ import annotations

import asyncio
from engine.cli.repl import EngineREPL, load_terminal_session


def main() -> None:
    session = load_terminal_session()
    raise SystemExit(asyncio.run(EngineREPL(session).run()))
