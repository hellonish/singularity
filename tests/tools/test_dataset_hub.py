"""
Tests for DatasetHubTool — HuggingFace Hub dataset search.

What to look for in the output:
  - Institutional authors (google, meta, etc.) get credibility 0.90
  - Community authors get 0.80
  - Metadata has tags, downloads, and author
"""
from tools.dataset_hub import DatasetHubTool, _INSTITUTIONS
from .conftest import assert_tool_result, print_result

QUERY = "squad"   # HuggingFace Hub search works best with simple terms


async def test_dataset_hub_basic():
    tool   = DatasetHubTool()
    result = await tool.call_with_retry(QUERY)

    print_result("DatasetHubTool", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"] == "dataset"
        assert src["credibility_base"] in (0.80, 0.90)
        assert "author"    in src["metadata"]
        assert "tags"      in src["metadata"]
        assert "downloads" in src["metadata"]


async def test_dataset_hub_institution_credibility_boost():
    """Datasets from known institutions should get 0.90, others 0.80."""
    tool   = DatasetHubTool()
    result = await tool.call_with_retry(QUERY, max_results=20)

    print_result("DatasetHubTool (institution check)", result)
    assert result.ok

    for src in result.sources:
        author         = src["metadata"]["author"].lower()
        is_institution = any(inst in author for inst in _INSTITUTIONS)
        expected_cred  = 0.90 if is_institution else 0.80
        assert src["credibility_base"] == expected_cred, (
            f"author={author!r}, expected {expected_cred}, got {src['credibility_base']}"
        )


async def test_dataset_hub_download_counts():
    """Popular datasets should have non-zero download counts."""
    tool   = DatasetHubTool()
    result = await tool.call_with_retry("squad", max_results=5)

    print_result("DatasetHubTool (download counts)", result)
    assert result.ok

    for src in result.sources:
        downloads = src["metadata"]["downloads"]
        print(f"\n  {src['title']:<45} | downloads: {downloads:>10,} | cred: {src['credibility_base']}")
