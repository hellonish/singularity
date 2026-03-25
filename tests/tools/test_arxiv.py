"""
Tests for ArxivTool — arXiv paper search.

What to look for in the output:
  - credibility 0.95 for papers with a journal_ref, 0.88 for preprints
  - Each source has pdf_url in metadata
  - Recency filter should reduce results when max_age_years is tight
"""
import pytest
from tools.arxiv_api import ArxivTool
from .conftest import assert_tool_result, print_result

QUERY = "large language model hallucination detection"


async def test_arxiv_basic():
    tool   = ArxivTool()
    result = await tool.call_with_retry(QUERY)

    print_result("ArxivTool", result)
    assert_tool_result(result)

    # Verify academic metadata is present
    for src in result.sources:
        assert src["source_type"] == "academic"
        assert "arxiv_id" in src["metadata"]
        assert "pdf_url"  in src["metadata"]


async def test_arxiv_recency_filter():
    """Filtering to last 1 year should return fewer or equal results than no filter."""
    tool = ArxivTool()

    result_all    = await tool.call_with_retry(QUERY, max_results=10)
    result_recent = await tool.call_with_retry(QUERY, max_results=10, max_age_years=1.0)

    print_result("ArxivTool (no filter)",   result_all,    max_sources=2)
    print_result("ArxivTool (1-year filter)", result_recent, max_sources=2)

    assert result_recent.ok
    assert len(result_recent.sources) <= len(result_all.sources)


async def test_arxiv_credibility_levels():
    """Published papers (journal_ref set) should get 0.95; preprints get 0.88."""
    tool   = ArxivTool()
    result = await tool.call_with_retry(QUERY, max_results=15)

    print_result("ArxivTool (credibility check)", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["credibility_base"] in (0.88, 0.95), (
            f"Unexpected credibility {src['credibility_base']} for {src['title'][:40]}"
        )
