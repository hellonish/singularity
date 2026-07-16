from __future__ import annotations

import pytest

from engine.research_workflow import checkpoint


class _Checkpointer:
    def __init__(self) -> None:
        self.setup_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _traceback) -> None:
        return None

    async def setup(self) -> None:
        self.setup_calls += 1


@pytest.mark.asyncio
async def test_checkpoint_context_does_not_run_schema_setup(monkeypatch) -> None:
    saver = _Checkpointer()
    monkeypatch.setattr(checkpoint, "create_checkpointer", lambda _url: saver)

    async with checkpoint.checkpoint_context("postgresql://example") as active:
        assert active is saver

    assert saver.setup_calls == 0


@pytest.mark.asyncio
async def test_setup_checkpointer_runs_schema_setup_once(monkeypatch) -> None:
    saver = _Checkpointer()
    monkeypatch.setattr(checkpoint, "create_checkpointer", lambda _url: saver)

    await checkpoint.setup_checkpointer("postgresql://example")

    assert saver.setup_calls == 1
