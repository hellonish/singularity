"""
Tests for StandardsFetchTool — NIST publications + IEEE Xplore.

What to look for in the output:
  - All sources have credibility 1.0
  - Metadata shows issuing_body (NIST or IEEE)
  - IEEE results only appear if IEEE_API_KEY is set
"""
import os
from tools.standards_fetch import StandardsFetchTool
from .conftest import assert_tool_result, print_result

QUERY = "cybersecurity framework risk management"


async def test_standards_fetch_basic():
    tool   = StandardsFetchTool()
    result = await tool.call_with_retry(QUERY)

    print_result("StandardsFetchTool", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"]      == "standard"
        assert src["credibility_base"] == 1.0
        assert "issuing_body" in src["metadata"]


async def test_standards_fetch_sources_labelled():
    """Each source should be labelled as NIST or IEEE."""
    tool   = StandardsFetchTool()
    result = await tool.call_with_retry(QUERY, max_results=10)

    print_result("StandardsFetchTool (source labels)", result)
    assert result.ok

    bodies = {src["metadata"]["issuing_body"] for src in result.sources}
    print(f"\n  Issuing bodies found: {bodies}")
    assert bodies <= {"NIST", "IEEE"}, f"Unexpected issuing body: {bodies}"


async def test_standards_fetch_ieee_only_when_key_set():
    """IEEE results should only appear when IEEE_API_KEY is configured."""
    tool   = StandardsFetchTool()
    result = await tool.call_with_retry(QUERY)

    assert result.ok
    ieee_sources = [s for s in result.sources if s["metadata"].get("issuing_body") == "IEEE"]

    if os.getenv("IEEE_API_KEY"):
        print(f"\n  IEEE_API_KEY set → {len(ieee_sources)} IEEE result(s)")
    else:
        print(f"\n  IEEE_API_KEY not set → expecting 0 IEEE results, got {len(ieee_sources)}")
        assert len(ieee_sources) == 0, "Should have no IEEE results without API key"
