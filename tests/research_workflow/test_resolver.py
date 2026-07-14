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


def test_test_mode_makes_exactly_one_search_and_one_fetch():
    """The real-inference test profile: 1 search variant + 1 fetch."""

    class EmptyThenNothing:
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

    executor = EmptyThenNothing()

    async def answerer(node, evidence):
        return {"answer": "answer", "answered": True}

    result = asyncio.run(
        BoundedResearchResolver(executor, answerer, max_fetches=1, max_search_variants=1)(
            ResearchNode(node_id="n1", question="question", section_id="s1", level=0),
            4,
        )
    )
    # Exactly one search and one fetch — the whole point of test mode.
    assert executor.calls == ["web_search", "web_fetch"]
    assert result["tool_calls_used"] == 2


def test_test_mode_does_not_reformulate_an_empty_search():
    """With one variant, an empty search is not retried with new queries."""

    class EmptyExecutor:
        def __init__(self):
            self.calls = []

        async def execute(self, invocation):
            self.calls.append(invocation.tool_name)
            return SimpleNamespace(content="", sources=[])

    executor = EmptyExecutor()

    async def answerer(node, evidence):  # pragma: no cover - no evidence, never runs
        raise AssertionError("answerer must not run without evidence")

    result = asyncio.run(
        BoundedResearchResolver(executor, answerer, max_fetches=1, max_search_variants=1)(
            ResearchNode(node_id="n1", question="question", section_id="s1", level=0),
            4,
        )
    )
    assert executor.calls == ["web_search"]
    assert result["answered"] is False


def test_resolver_rejects_out_of_range_budget():
    async def answerer(node, evidence):
        return {"answer": "answer"}

    for bad_budget in (0, 9):
        with pytest.raises(ValueError, match="between 1 and"):
            asyncio.run(
                BoundedResearchResolver(FakeExecutor(), answerer)(
                    ResearchNode(node_id="n1", question="question", section_id="s1", level=0),
                    bad_budget,
                )
            )


def test_resolver_routes_domain_questions_to_specialized_tools():
    """A medical question dispatches pubmed/clinicaltrials before web search."""

    class RoutingExecutor:
        def __init__(self):
            self.calls = []

        async def execute(self, invocation):
            self.calls.append(invocation.tool_name)
            return SimpleNamespace(
                content=f"{invocation.tool_name} body",
                sources=[{
                    "title": invocation.tool_name,
                    "url": f"https://{invocation.tool_name}.example",
                    "snippet": "snippet",
                    "source_type": invocation.tool_name,
                }],
            )

    executor = RoutingExecutor()

    async def answerer(node, evidence):
        return {"answer": "answer", "answered": True}

    question = "latest clinical trial results for a new drug treating this disease (pubmed)"
    result = asyncio.run(
        BoundedResearchResolver(executor, answerer)(
            ResearchNode(node_id="n1", question=question, section_id="s1", level=0),
            5,
        )
    )
    # Domain discovery tools run first, then the general web pass and a fetch.
    assert executor.calls[0] == "pubmed"
    assert "clinicaltrials" in executor.calls
    assert "web_search" in executor.calls
    assert result["answered"] is True


def test_resolver_falls_back_to_web_when_domain_tool_errors():
    """A domain tool that returns an error is a soft failure; web still answers."""

    class DomainFailsExecutor:
        def __init__(self):
            self.calls = []

        async def execute(self, invocation):
            self.calls.append(invocation.tool_name)
            if invocation.tool_name in {"pubmed", "clinicaltrials"}:
                return SimpleNamespace(content="", sources=[], error="upstream 503")
            if invocation.tool_name == "web_search":
                return SimpleNamespace(
                    content="search result",
                    sources=[{"title": "One", "url": "https://one.example", "snippet": "one"}],
                )
            return SimpleNamespace(
                content="page text",
                sources=[{"title": "Fetched", "url": invocation.arguments["url"], "snippet": "page"}],
            )

    executor = DomainFailsExecutor()

    async def answerer(node, evidence):
        return {"answer": "answer", "answered": True}

    question = "clinical trial drug disease pubmed evidence"
    result = asyncio.run(
        BoundedResearchResolver(executor, answerer)(
            ResearchNode(node_id="n1", question=question, section_id="s1", level=0),
            5,
        )
    )
    assert "web_search" in executor.calls
    assert result["answered"] is True
    assert all(str(item["url"]).startswith("https://one") for item in result["evidence"])


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


def test_resolver_skips_one_unreachable_fetch_and_keeps_other_evidence(monkeypatch):
    """One slow source must not discard a research node with usable evidence."""
    import engine.research_workflow.resolver as resolver_module

    # Avoid sleeping through dispatch retries in this deterministic unit test;
    # the behavior under test is the source-level handling after retries end.
    monkeypatch.setattr(resolver_module, "_MODAL_DISPATCH_ATTEMPTS", 1)
    events = []

    class OneSlowSourceExecutor:
        async def execute(self, invocation):
            if invocation.tool_name == "web_search":
                return SimpleNamespace(
                    content="search results",
                    sources=[
                        {"title": "Slow", "url": "https://slow.example", "snippet": "slow result"},
                        {"title": "Fast", "url": "https://fast.example", "snippet": "fast result"},
                    ],
                )
            if invocation.arguments["url"] == "https://slow.example":
                raise TimeoutError()
            return SimpleNamespace(
                content="retrieved page",
                sources=[{"title": "Fast", "url": "https://fast.example", "snippet": "fast page"}],
            )

    async def answerer(node, evidence):
        assert any(item["url"] == "https://fast.example" for item in evidence)
        return {"answer": "answer", "answered": True}

    result = asyncio.run(
        BoundedResearchResolver(OneSlowSourceExecutor(), answerer, progress_reporter=events.append)(
            ResearchNode(node_id="n1", question="question", section_id="s1", level=0), 4
        )
    )

    assert result["answered"] is True
    assert any(event["status"] == "source_unavailable" for event in events)
