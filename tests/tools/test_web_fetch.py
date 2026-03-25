"""
Tests for WebFetchTool — DuckDuckGo + Tavily fallback.

What to look for in the output:
  - Sources from .gov/.edu should show credibility 0.85
  - General web sources should show credibility 0.75
  - Snippets are extracted from the page body
"""
import pytest
from tools.web_fetch import WebFetchTool
from .conftest import assert_tool_result, print_result

QUERY = "GDPR implications of using third-party LLM APIs for processing EU customer data"


async def test_web_fetch_basic():
    tool   = WebFetchTool()
    result = await tool.call_with_retry(QUERY)

    print_result("WebFetchTool", result)
    assert_tool_result(result)


async def test_web_fetch_gov_sources_get_credibility_boost():
    """Gov/edu URLs should have credibility_base 0.85, not 0.75."""
    tool   = WebFetchTool()
    result = await tool.call_with_retry("GDPR official text european commission")

    print_result("WebFetchTool (gov/edu query)", result)
    assert_tool_result(result)

    gov_sources = [s for s in result.sources if ".gov" in s["url"] or ".europa.eu" in s["url"]]
    if gov_sources:
        for src in gov_sources:
            assert src["credibility_base"] == 0.85, (
                f"Expected 0.85 for gov source, got {src['credibility_base']}: {src['url']}"
            )


async def test_web_fetch_max_results_respected():
    tool   = WebFetchTool()
    result = await tool.call_with_retry(QUERY, max_results=5)

    print_result("WebFetchTool (max_results=5)", result)
    assert_tool_result(result)
    assert len(result.sources) <= 5
