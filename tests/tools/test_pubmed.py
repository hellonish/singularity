"""
Tests for PubMedTool — NCBI PubMed via Biopython Entrez.

Requires: NCBI_EMAIL env var (free, just an email address).

What to look for in the output:
  - Each source has PMID, journal name, and MeSH terms in metadata
  - Preprints (bioRxiv/medRxiv) get credibility 0.85; peer-reviewed get 0.92
  - Authors list is populated
"""
import os
import pytest
from tools.pubmed_api import PubMedTool
from .conftest import assert_tool_result, print_result

QUERY = "mRNA vaccine efficacy COVID-19 randomized controlled trial"


@pytest.mark.skipif(
    not os.getenv("NCBI_EMAIL"),
    reason="NCBI_EMAIL env var required for PubMed access"
)
async def test_pubmed_basic():
    tool   = PubMedTool()
    result = await tool.call_with_retry(QUERY)

    print_result("PubMedTool", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"] == "academic"
        assert "pmid"    in src["metadata"]
        assert "journal" in src["metadata"]
        assert "mesh"    in src["metadata"]
        assert src["url"].startswith("https://pubmed.ncbi.nlm.nih.gov/")


@pytest.mark.skipif(
    not os.getenv("NCBI_EMAIL"),
    reason="NCBI_EMAIL env var required for PubMed access"
)
async def test_pubmed_credibility_levels():
    """Peer-reviewed sources should score 0.92; preprints 0.85."""
    tool   = PubMedTool()
    result = await tool.call_with_retry(QUERY, max_results=15)

    print_result("PubMedTool (credibility check)", result)
    assert result.ok

    for src in result.sources:
        assert src["credibility_base"] in (0.85, 0.92), (
            f"Unexpected credibility {src['credibility_base']} for '{src['title'][:40]}'"
        )


@pytest.mark.skipif(
    not os.getenv("NCBI_EMAIL"),
    reason="NCBI_EMAIL env var required for PubMed access"
)
async def test_pubmed_authors_populated():
    tool   = PubMedTool()
    result = await tool.call_with_retry("CRISPR gene editing clinical applications", max_results=5)

    print_result("PubMedTool (authors check)", result)
    assert result.ok

    sourced_with_authors = [s for s in result.sources if s.get("authors")]
    assert len(sourced_with_authors) > 0, "Expected at least one source with authors"
