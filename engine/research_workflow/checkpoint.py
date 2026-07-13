from __future__ import annotations

from contextlib import asynccontextmanager


def create_checkpointer(database_url: str):
    """Return the LangGraph async checkpointer for the configured database.

    The import is intentionally lazy: API schema and unit-test processes do not
    need the optional LangGraph packages, while production workers fail clearly
    if the checkpoint dependency has not been installed.
    """
    if database_url.startswith("postgres"):
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("install langgraph-checkpoint-postgres for PostgreSQL checkpoints") from exc
        checkpoint_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return AsyncPostgresSaver.from_conn_string(checkpoint_url)
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install langgraph-checkpoint-sqlite for local checkpoints") from exc
    path = database_url.rsplit("/", 1)[-1].split("?", 1)[0] or "research_checkpoints.sqlite"
    return AsyncSqliteSaver.from_conn_string(path)


@asynccontextmanager
async def checkpoint_context(database_url: str):
    """Open, initialize, and close the durable checkpointer correctly."""
    manager = create_checkpointer(database_url)
    async with manager as checkpointer:
        setup = getattr(checkpointer, "setup", None)
        if setup is not None:
            await setup()
        yield checkpointer
