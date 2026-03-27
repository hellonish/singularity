"""
Shared helpers for tool tests.

Running a single tool:
    pytest tests/tools/test_web_fetch.py -v -s

Running all tool tests:
    pytest tests/tools/ -v -s

Each test calls the real API. Set the relevant env vars before running:
    NCBI_EMAIL            PubMed
    GITHUB_TOKEN          GitHub (optional, raises rate limit)
    TAVILY_API_KEY        Tavily web search fallback (optional)
    GOOGLE_BOOKS_API_KEY  Google Books (optional)
    IEEE_API_KEY          IEEE Xplore standards (optional)
    LIBRETRANSLATE_URL    LibreTranslate instance (optional, defaults to public)
    LIBRETRANSLATE_API_KEY  LibreTranslate API key (optional)
"""
from tools.base import ToolResult


def print_result(tool_name: str, result: ToolResult, max_sources: int = 3) -> None:
    """Pretty-print a ToolResult so it's easy to inspect during test runs."""
    bar = "─" * 60
    print(f"\n{bar}")
    if not result.ok:
        print(f"  {tool_name}  ✗  ERROR: {result.error}")
        print(bar)
        return

    print(f"  {tool_name}  ✓  {len(result.sources)} source(s)  |  cred: {result.credibility_base:.2f}")
    print(bar)
    for i, src in enumerate(result.sources[:max_sources], 1):
        cred    = src.get("credibility_base", 0.0)
        title   = src.get("title", "—")[:65]
        url     = src.get("url",   "—")[:70]
        snippet = (src.get("snippet") or "")[:120].replace("\n", " ")
        date    = src.get("date", "")
        print(f"  [{i}] [{cred:.2f}] {title}")
        print(f"       url     : {url}")
        if date:
            print(f"       date    : {date}")
        if snippet:
            print(f"       snippet : {snippet}")
    if len(result.sources) > max_sources:
        print(f"  ... and {len(result.sources) - max_sources} more source(s)")
    print(bar)


def assert_tool_result(result: ToolResult) -> None:
    """Assert the ToolResult satisfies the base contract."""
    assert result.ok,                       f"Tool returned an error: {result.error}"
    assert isinstance(result.content, str), "content must be a string"
    assert len(result.sources) > 0,         "sources list must not be empty"
    assert 0.0 <= result.credibility_base <= 1.0, "credibility_base must be 0–1"
    for src in result.sources:
        assert "title"            in src
        assert "url"              in src
        assert "credibility_base" in src
        assert 0.0 <= src["credibility_base"] <= 1.0
