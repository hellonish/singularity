import asyncio
from dataclasses import dataclass

import pytest

from engine.chat.effort import ChatEffort
from engine.chat.modal_tools import ChatToolResult
from engine.chat.tool_loop import BoundedChatToolLoop, PlannedToolCall, ToolExecutionTimeout, ToolPlanningTimeout


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
        ]
    )
    executor = FakeExecutor()

    results = asyncio.run(
        BoundedChatToolLoop(planner=planner, executor=executor).run(
            run_id="run_1", query="research", effort=ChatEffort.INSTANT, context=""
        )
    )

    assert len(results) == 1
    assert len(executor.invocations) == 1
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
    assert events[1][1] == "medical_research/pubmed"
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


def test_tool_loop_identifies_execution_timeout_after_dispatch() -> None:
    class TimeoutExecutor:
        async def execute(self, invocation):
            raise TimeoutError

    planner = FakePlanner([PlannedToolCall("medical_research", "pubmed", "query", {})])
    with pytest.raises(ToolExecutionTimeout, match="pubmed timed out"):
        asyncio.run(BoundedChatToolLoop(planner=planner, executor=TimeoutExecutor()).run(
            run_id="run_1", query="search", effort=ChatEffort.INSTANT, context=""
        ))
