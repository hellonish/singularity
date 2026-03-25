"""
Tests for ClinicalTrialsTool — ClinicalTrials.gov v2 REST API.

What to look for in the output:
  - All sources have credibility 1.0 (official registry)
  - Metadata shows phase (I/II/III/IV), status, and conditions
  - has_results flag tells if results have been published
"""
from tools.clinicaltrials import ClinicalTrialsTool
from .conftest import assert_tool_result, print_result

QUERY = "GLP-1 receptor agonist type 2 diabetes weight loss"


async def test_clinicaltrials_basic():
    tool   = ClinicalTrialsTool()
    result = await tool.call_with_retry(QUERY)

    print_result("ClinicalTrialsTool", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"] == "clinical"
        assert src["credibility_base"] == 1.0
        assert src["url"].startswith("https://clinicaltrials.gov/study/")
        assert "nct_id"  in src["metadata"]
        assert "status"  in src["metadata"]
        assert "phase"   in src["metadata"]


async def test_clinicaltrials_metadata_detail():
    """Conditions and interventions should be populated for most results."""
    tool   = ClinicalTrialsTool()
    result = await tool.call_with_retry(QUERY, max_results=5)

    print_result("ClinicalTrialsTool (metadata detail)", result)
    assert result.ok

    for src in result.sources:
        meta = src["metadata"]
        print(f"\n  NCT: {meta['nct_id']} | Phase: {meta['phase']} | Status: {meta['status']}")
        print(f"  Conditions  : {meta.get('conditions', [])[:3]}")
        print(f"  Interventions: {meta.get('interventions', [])[:3]}")
        print(f"  Has results : {meta.get('has_results')}")


async def test_clinicaltrials_nct_id_format():
    """NCT IDs should follow the NCT + 8-digit format."""
    tool   = ClinicalTrialsTool()
    result = await tool.call_with_retry("Alzheimer disease treatment amyloid", max_results=5)

    assert result.ok
    for src in result.sources:
        nct = src["metadata"]["nct_id"]
        assert nct.startswith("NCT"), f"Unexpected NCT ID format: {nct}"
        assert len(nct) == 11,        f"NCT ID should be 11 chars, got: {nct}"
