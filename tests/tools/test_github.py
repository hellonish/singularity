"""
Tests for GitHubTool — GitHub repository search via PyGithub.

What to look for in the output:
  - credibility ranges from 0.70 (few stars) to 0.90 (1000+ stars)
  - Metadata shows stars, language, and license
  - README snippet gives context on what the repo does

Set GITHUB_TOKEN for higher rate limits (5000 req/hr vs 60).
"""
import os
from tools.github_api import GitHubTool
from .conftest import assert_tool_result, print_result

QUERY = "LLM inference serving"


async def test_github_basic():
    tool   = GitHubTool()
    result = await tool.call_with_retry(QUERY)

    print_result("GitHubTool", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"] == "code"
        assert 0.70 <= src["credibility_base"] <= 0.90
        assert "stars"    in src["metadata"]
        assert "language" in src["metadata"]


async def test_github_credibility_scales_with_stars():
    """High-star repos should get higher credibility than low-star repos."""
    tool   = GitHubTool()
    result = await tool.call_with_retry(QUERY, max_results=10)

    print_result("GitHubTool (credibility vs stars)", result)
    assert result.ok

    for src in result.sources:
        stars    = src["metadata"]["stars"]
        cred     = src["credibility_base"]
        expected = round(min(0.90, 0.70 + min(0.20, (stars / 1000) * 0.20)), 3)
        assert abs(cred - expected) < 0.001, (
            f"stars={stars}, expected cred≈{expected}, got {cred}"
        )


async def test_github_readme_in_snippet():
    """Snippet should come from the repo README (not just description)."""
    tool   = GitHubTool()
    result = await tool.call_with_retry("pytorch deep learning framework", max_results=3)

    print_result("GitHubTool (readme snippet)", result)
    assert result.ok

    sources_with_content = [s for s in result.sources if len(s.get("snippet", "")) > 30]
    assert len(sources_with_content) > 0, "Expected at least one source with a non-trivial snippet"


async def test_github_rate_limit_note():
    """Just prints whether running authenticated or not."""
    token = os.getenv("GITHUB_TOKEN")
    print(f"\n  GITHUB_TOKEN: {'set (5000 req/hr)' if token else 'not set (60 req/hr)'}")
    assert True  # informational only
