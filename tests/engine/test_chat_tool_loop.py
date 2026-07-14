import asyncio
from dataclasses import dataclass

import pytest

from engine.chat.effort import ChatEffort
from engine.chat.modal_tools import ChatToolResult
from engine.chat.tool_loop import BoundedChatToolLoop, PlannedToolBatch, PlannedToolCall, ToolPlanningTimeout


@dataclass
class FakePlanner:
    calls: list[PlannedToolCall]

    async def plan(self, **kwargs):
        return self.calls.pop(0) if self.calls else None


class FakeExecutor:
    def __init__(self) -> None:
        self.invocations = []

    async def execute(self, invocation):
        self.invocations.append(invocation)
        return ChatToolResult(content="tool result", sources=[], credibility_base=0.8, error=None)


def test_tool_loop_enforces_profile_tool_type_cap() -> None:
    planner = FakePlanner(
        [
            PlannedToolCall("medical_research", "pubmed", "first", {"max_results": 1}),
            PlannedToolCall("medical_research", "pubmed", "second", {"max_results": 1}),
            PlannedToolCall("medical_research", "pubmed", "third", {"max_results": 1}),
        ]
    )
    executor = FakeExecutor()

    results = asyncio.run(
        BoundedChatToolLoop(planner=planner, executor=executor).run(
            run_id="run_1", query="research", effort=ChatEffort.INSTANT, context=""
        )
    )

    assert len(results) == 2
    assert len(executor.invocations) == 2
    assert results[0].tool_name == "pubmed"


def test_tool_loop_rejects_invalid_arguments_before_executor_dispatch() -> None:
    planner = FakePlanner(
        [PlannedToolCall("medical_research", "pubmed", "first", {"unexpected": "value"})]
    )
    executor = FakeExecutor()

    try:
        asyncio.run(
            BoundedChatToolLoop(planner=planner, executor=executor).run(
                run_id="run_1", query="research", effort=ChatEffort.INSTANT, context=""
            )
        )
    except Exception as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("expected invalid arguments to stop the loop")

    assert executor.invocations == []


def test_tool_result_redaction_covers_sources() -> None:
    planner = FakePlanner([PlannedToolCall("medical_research", "pubmed", "first", {})])

    class SecretExecutor:
        async def execute(self, invocation):
            return ChatToolResult(
                content="authorization=secret",
                sources=[{"snippet": "api_key: secret"}],
                credibility_base=0.8,
                error=None,
            )

    results = asyncio.run(
        BoundedChatToolLoop(planner=planner, executor=SecretExecutor()).run(
            run_id="run_1", query="research", effort=ChatEffort.INSTANT, context=""
        )
    )

    assert "secret" not in results[0].result.content
    assert "secret" not in results[0].result.sources[0]["snippet"]


def test_tool_loop_emits_compact_lifecycle_progress() -> None:
    planner = FakePlanner([PlannedToolCall("medical_research", "pubmed", "first", {})])
    events = []

    async def progress(kind, content, elapsed):
        events.append((kind, content, elapsed))

    asyncio.run(
        BoundedChatToolLoop(planner=planner, executor=FakeExecutor()).run(
            run_id="run_1",
            query="research",
            effort=ChatEffort.INSTANT,
            context="",
            progress_callback=progress,
        )
    )

    # The single planned call yields plan→start→completed; any trailing
    # planning rounds (from the profile's step budget) resolve to no tool.
    assert [event[0] for event in events][:3] == ["tool_planning_start", "tool_start", "tool_completed"]
    assert [event[0] for event in events].count("tool_start") == 1
    assert events[1][1] == 'pubmed(query=\'first\', arguments={})'
    assert events[2][2] is not None


def test_tool_loop_identifies_planning_timeout_before_dispatch() -> None:
    class TimeoutPlanner:
        async def plan(self, **kwargs):
            raise TimeoutError

    executor = FakeExecutor()
    with pytest.raises(ToolPlanningTimeout, match="no tool was dispatched"):
        asyncio.run(BoundedChatToolLoop(planner=TimeoutPlanner(), executor=executor).run(
            run_id="run_1", query="search", effort=ChatEffort.INSTANT, context=""
        ))
    assert executor.invocations == []


def test_tool_loop_preserves_execution_timeout_as_a_failed_observation() -> None:
    class TimeoutExecutor:
        async def execute(self, invocation):
            raise TimeoutError

    planner = FakePlanner([PlannedToolCall("medical_research", "pubmed", "query", {})])
    results = asyncio.run(BoundedChatToolLoop(planner=planner, executor=TimeoutExecutor()).run(
        run_id="run_1", query="search", effort=ChatEffort.INSTANT, context=""
    ))
    assert len(results) == 1
    assert "timed out" in str(results[0].result.error)


def test_tool_loop_executes_independent_batch_in_parallel_and_routes_second_search_to_tavily() -> None:
    class BatchPlanner:
        def __init__(self) -> None:
            self.used = False

        async def plan(self, **kwargs):
            if self.used:
                return None
            self.used = True
            return PlannedToolBatch(calls=(
                PlannedToolCall("general_web_research", "web_search", "one", {"max_results": 1}),
                PlannedToolCall("general_web_research", "web_search", "two", {"max_results": 1}),
            ))

    class ParallelExecutor(FakeExecutor):
        def __init__(self) -> None:
            super().__init__()
            self.active = 0
            self.max_active = 0

        async def execute(self, invocation):
            self.invocations.append(invocation)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            await asyncio.sleep(0.01)
            self.active -= 1
            return ChatToolResult(content="result", sources=[], credibility_base=0.8, error=None)

    executor = ParallelExecutor()
    results = asyncio.run(BoundedChatToolLoop(planner=BatchPlanner(), executor=executor).run(
        run_id="run_1", query="latest", effort=ChatEffort.INSTANT, context=""
    ))

    assert len(results) == 2
    assert executor.max_active == 2
    assert executor.invocations[0].arguments.get("search_backend", "auto") == "auto"
    assert executor.invocations[1].arguments["search_backend"] == "tavily"
