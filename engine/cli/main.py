from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from engine.cli.repl import EngineREPL, load_terminal_session


def main() -> None:
    # The direct terminal runtime owns its Modal configuration.  Load the
    # checkout's .env without overriding explicit shell/CI environment values.
    load_dotenv()
    session = load_terminal_session()
    raise SystemExit(asyncio.run(EngineREPL(session).run()))
