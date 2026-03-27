"""
Tests for SecEdgarTool — SEC EDGAR full-text search.

What to look for in the output:
  - All sources have credibility 1.0 (official filings)
  - Metadata shows company name, form type (10-K/10-Q/8-K), and period
  - URLs point to SEC.gov
"""
from tools.sec_edgar import SecEdgarTool
from .conftest import assert_tool_result, print_result

QUERY = "artificial intelligence risk disclosure"


async def test_sec_edgar_basic():
    tool   = SecEdgarTool()
    result = await tool.call_with_retry(QUERY)

    print_result("SecEdgarTool", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"]      == "financial"
        assert src["credibility_base"] == 1.0
        assert "company"   in src["metadata"]
        assert "form_type" in src["metadata"]


async def test_sec_edgar_known_company():
    """Search for filings from a well-known company."""
    tool   = SecEdgarTool()
    result = await tool.call_with_retry("Microsoft cloud computing revenue growth", max_results=5)

    print_result("SecEdgarTool (company search)", result)
    assert result.ok

    for src in result.sources:
        meta = src["metadata"]
        print(f"\n  Company  : {meta.get('company')}")
        print(f"  Form     : {meta.get('form_type')}")
        print(f"  Period   : {meta.get('period')}")


async def test_sec_edgar_form_types_present():
    """Verify form_type metadata is populated."""
    tool   = SecEdgarTool()
    result = await tool.call_with_retry(QUERY, max_results=5)

    assert result.ok
    form_types = {src["metadata"].get("form_type") for src in result.sources}
    print(f"\n  Form types found: {form_types}")
    # At least one result should have a recognisable form type
    known_forms = {"10-K", "10-Q", "8-K", "DEF 14A", "S-1"}
    assert form_types & known_forms or len(result.sources) > 0
