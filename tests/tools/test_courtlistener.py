"""
Tests for CourtListenerTool — US case law, free REST API.

What to look for in the output:
  - All sources have credibility 1.0 (official court records)
  - Metadata contains court, citation, and docket_num fields
  - URLs point to courtlistener.com
"""
from tools.courtlistener import CourtListenerTool
from .conftest import assert_tool_result, print_result

QUERY = "data privacy Fourth Amendment digital search warrant"


async def test_courtlistener_basic():
    tool   = CourtListenerTool()
    result = await tool.call_with_retry(QUERY)

    print_result("CourtListenerTool", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"] == "legal"
        assert src["credibility_base"] == 0.95
        assert "court"  in src["metadata"]
        assert src["url"].startswith("https://www.courtlistener.com")


async def test_courtlistener_specific_case_type():
    """Search for a landmark privacy case."""
    tool   = CourtListenerTool()
    result = await tool.call_with_retry("Carpenter v United States cell phone location data", max_results=5)

    print_result("CourtListenerTool (landmark case)", result)
    assert result.ok
    assert len(result.sources) >= 1


async def test_courtlistener_metadata_fields():
    """Verify all expected metadata fields are present."""
    tool   = CourtListenerTool()
    result = await tool.call_with_retry(QUERY, max_results=3)

    assert result.ok
    for src in result.sources:
        meta = src["metadata"]
        for field in ("court", "citation", "status", "docket_num"):
            assert field in meta, f"Missing metadata field: {field}"
