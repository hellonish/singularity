"""
Tests for SemanticScholarTool — Semantic Scholar Graph API.

What to look for in the output:
  - Papers with >50 citations get credibility 0.95; others get 0.90
  - Open-access papers have a PDF url
  - citation_count is in metadata
"""
import asyncio
import pytest
from tools.semantic_scholar import SemanticScholarTool
from .conftest import assert_tool_result, print_result

QUERY = "transformer attention mechanism neural networks"


@pytest.fixture(autouse=True)
async def pace_requests():
    """Space tests 5 s apart — Semantic Scholar rate-limits unauthenticated callers."""
    await asyncio.sleep(5)
    yield


def _skip_if_rate_limited(result) -> None:
    """Call after call_with_retry; skip the test if we hit a 429 window."""
    if not result.ok and "rate limit" in (result.error or "").lower():
        pytest.skip("Semantic Scholar rate limit active — wait 5 min and retry")


async def test_semantic_scholar_basic():
    tool   = SemanticScholarTool()
    result = await tool.call_with_retry(QUERY)
    _skip_if_rate_limited(result)

    print_result("SemanticScholarTool", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"] == "academic"
        assert "paper_id"      in src["metadata"]
        assert "citation_count" in src["metadata"]
        assert isinstance(src["metadata"]["citation_count"], int)


async def test_semantic_scholar_credibility_boost_for_highly_cited():
    """Papers with >50 citations should get 0.95; others 0.90."""
    tool   = SemanticScholarTool()
    result = await tool.call_with_retry(QUERY, max_results=20)
    _skip_if_rate_limited(result)

    print_result("SemanticScholarTool (credibility check)", result)
    assert result.ok

    for src in result.sources:
        count    = src["metadata"]["citation_count"]
        expected = 0.95 if count > 50 else 0.90
        assert src["credibility_base"] == expected, (
            f"citations={count}, expected cred={expected}, got {src['credibility_base']}"
        )


async def test_semantic_scholar_open_access_papers():
    """Open-access papers should have a non-empty URL."""
    tool   = SemanticScholarTool()
    result = await tool.call_with_retry("BERT language model pre-training", max_results=10)
    _skip_if_rate_limited(result)

    print_result("SemanticScholarTool (open access)", result)
    assert result.ok

    open_access = [s for s in result.sources if s["metadata"].get("open_access")]
    print(f"\n  Open-access papers: {len(open_access)} / {len(result.sources)}")
    for src in open_access:
        assert src["url"], "Open-access paper should have a URL"
