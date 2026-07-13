"""One executable LangGraph research workflow used by the CLI and worker."""
from __future__ import annotations

import warnings
from inspect import isawaitable
from dataclasses import asdict
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

from .caps import RunCaps
from .langgraph_runtime import build_research_graph


class ResearchWorkflow:
    def __init__(self, *, planner, lead, resolver, qa_reviewer, writer, checkpointer=None) -> None:
        # langgraph-checkpoint 2.x constructs its legacy serializer while
        # importing it. Newer langchain-core versions warn because that
        # dependency does not yet pass ``allowed_objects`` explicitly. Our
        # graph state is plain JSON-compatible data, so suppress only that
        # dependency warning until the checkpoint package is updated.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="The default value of `allowed_objects` will change.*",
                category=LangChainPendingDeprecationWarning,
            )
            if checkpointer is None:
                from langgraph.checkpoint.memory import MemorySaver
                checkpointer = MemorySaver()
            self._progress_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None
            self.graph = build_research_graph(
                planner=planner,
                lead=lead,
                resolver=resolver,
                qa_reviewer=qa_reviewer,
                writer=writer,
                checkpointer=checkpointer,
                progress_reporter=self._emit_progress,
            )

    async def _emit_progress(self, event: dict[str, Any]) -> None:
        if self._progress_callback is not None:
            result = self._progress_callback(event)
            if isawaitable(result):
                await result

    async def run(
        self,
        *,
        run_id: str,
        query: str,
        caps: RunCaps,
        on_update: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
        on_progress: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        config = {"configurable": {"thread_id": run_id}}
        initial = {
            "run_id": run_id,
            "query": query,
            "caps": asdict(caps),
            "cycle": 0,
            "events": [],
            "qa_reviews": [],
        }
        self._progress_callback = on_progress
        try:
            if on_update is None:
                return await self.graph.ainvoke(initial, config)
            async for update in self.graph.astream(initial, config, stream_mode="updates"):
                for node_name, payload in update.items():
                    await on_update(str(node_name), dict(payload))
            snapshot = await self.graph.aget_state(config)
            return dict(snapshot.values)
        finally:
            self._progress_callback = None

    async def resume(self, *, run_id: str) -> dict[str, Any]:
        return await self.graph.ainvoke(None, {"configurable": {"thread_id": run_id}})
