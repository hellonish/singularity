"""One-shot LangGraph checkpoint schema setup for the migration service."""
from __future__ import annotations

import asyncio

from api.config import settings
from engine.research_workflow.checkpoint import setup_checkpointer


async def main() -> None:
    await setup_checkpointer(settings.database_url)


if __name__ == "__main__":
    asyncio.run(main())
