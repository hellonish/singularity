import asyncio
from types import SimpleNamespace

import pytest

from engine.research_workflow.dag import ResearchNode
from engine.research_workflow.resolver import BoundedResearchResolver
from engine.research_workflow.runtime import ResearchInfrastructureError


class FakeExecutor:
    def __init__(self):
        self.calls = []

    async def execute(self, invocation):
        self.calls.append(invocation.tool_name)
        if invocation.tool_name == "web_search":
            return SimpleNamespace(
                content="search result",
                sources=[
                    {"title": "One", "url": "https://one.example", "snippet": "one"},
                    {"title": "Two", "url": "https://two.example", "snippet": "two"},
                ],
            )
        return SimpleNamespace(
            content="page text",
            sources=[{"title": "Fetched", "url": invocation.arguments["url"], "snippet": "page"}],
        )


def test_resolver_uses_search_and_two_fetches_within_four_call_budget():
    executor = FakeExecutor()
    events = []

    async def answerer(node, evidence):
        return {"answer": "answer", "answered": True}

    async def report(event):
        events.append(event)

    result = asyncio.run(
        BoundedResearchResolver(executor, answerer, progress_reporter=report)(
            ResearchNode(node_id="n1", question="question", section_id="s1", level=0),
            4,
        )
    )
    assert executor.calls == ["web_search", "web_fetch", "web_fetch"]
    assert result["tool_calls_used"] == 3
    assert events[0]["status"] == "node_started"
    assert [event["status"] for event in events].count("tool_dispatched") == 3
    assert [event["status"] for event in events].count("tool_completed") == 3
    assert events[-1]["status"] == "node_completed"


def test_resolver_rejects_non_four_budget():
    async def answerer(node, evidence):
        return {"answer": "answer"}

    with pytest.raises(ValueError, match="four-call"):
        asyncio.run(
            BoundedResearchResolver(FakeExecutor(), answerer)(
                ResearchNode(node_id="n1", question="question", section_id="s1", level=0),
                3,
            )
        )


def test_resolver_accepts_a_synchronous_progress_renderer():
    events = []

    async def answerer(node, evidence):
        return {"answer": "answer", "answered": True}

    result = asyncio.run(
        BoundedResearchResolver(FakeExecutor(), answerer, progress_reporter=events.append)(
            ResearchNode(node_id="n1", question="question", section_id="s1", level=0), 4
        )
    )

    assert result["answered"] is True
    assert events[0]["status"] == "node_started"


def test_resolver_does_not_generate_an_answer_without_citable_evidence():
    class EmptyExecutor:
        async def execute(self, invocation):
            return SimpleNamespace(content="", sources=[])

    called = False

    async def answerer(node, evidence):
        nonlocal called
        called = True
        return {"answer": "unsupported"}

    result = asyncio.run(
        BoundedResearchResolver(EmptyExecutor(), answerer)(
            ResearchNode(node_id="n1", question="question", section_id="s1", level=0), 4
        )
    )

    assert called is False
    assert result["answered"] is False
    # An empty result is a soft failure: the resolver reformulates the query
    # and tries each variant until the four-call budget is spent.
    assert result["tool_calls_used"] == 3


def test_resolver_raises_infrastructure_error_when_backend_stays_unreachable():
    class DownExecutor:
        def __init__(self):
            self.attempts = 0

        async def execute(self, invocation):
            self.attempts += 1
            raise ConnectionError("modal channel dropped")

    executor = DownExecutor()

    async def answerer(node, evidence):  # pragma: no cover - must never run
        raise AssertionError("answerer must not run when the backend is down")

    with pytest.raises(ResearchInfrastructureError):
        asyncio.run(
            BoundedResearchResolver(executor, answerer)(
                ResearchNode(node_id="n1", question="question", section_id="s1", level=0), 4
            )
        )
    # One logical call, retried across every dispatch attempt before giving up.
    assert executor.attempts >= 2


def test_resolver_recovers_when_a_transient_dispatch_failure_then_succeeds():
    class FlakyExecutor:
        def __init__(self):
            self.attempts = 0

        async def execute(self, invocation):
            self.attempts += 1
            if invocation.tool_name == "web_search" and self.attempts == 1:
                raise ConnectionError("transient blip")
            if invocation.tool_name == "web_search":
                return SimpleNamespace(
                    content="ok",
                    sources=[{"title": "T", "url": "https://ok.example", "snippet": "s"}],
                )
            return SimpleNamespace(content="page", sources=[{"title": "F", "url": invocation.arguments["url"], "snippet": "p"}])

    executor = FlakyExecutor()

    async def answerer(node, evidence):
        return {"answer": "answer", "answered": True}

    result = asyncio.run(
        BoundedResearchResolver(executor, answerer)(
            ResearchNode(node_id="n1", question="question", section_id="s1", level=0), 4
        )
    )
    assert result["answered"] is True
    # The first dispatch failed and was retried transparently within the same
    # logical search call, so the node still resolves.
    assert result["tool_calls_used"] <= 4
