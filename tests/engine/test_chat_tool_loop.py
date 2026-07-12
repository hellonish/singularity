import asyncio
from dataclasses import dataclass

from engine.chat.effort import ChatEffort
from engine.chat.modal_tools import ChatToolResult
from engine.chat.tool_loop import BoundedChatToolLoop, PlannedToolCall


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

    assert [event[0] for event in events] == ["thinking", "tool_start", "tool_completed"]
    assert events[1][1] == "medical_research/pubmed"
    assert events[2][2] is not None
