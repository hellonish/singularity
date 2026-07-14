from __future__ import annotations

import asyncio
import socket

import pytest

from engine.tools.calculator import CalculatorTool, calculate
from engine.tools.current_time import CurrentTimeTool
from engine.tools.url_safety import validate_public_url
from engine.tools.web_fetch import _extract
from engine.tools.web_search import WebSearchTool
import engine.tools.web_search as web_search_module


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3 * 4", 14),
        ("20% of 50", 10.0),
        ("convert 1 km to m", 1000.0),
        ("mean([1, 2, 6])", 3),
    ],
)
def test_calculator_supports_deterministic_general_operations(expression, expected) -> None:
    assert calculate(expression) == expected


def test_calculator_rejects_code_execution() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        calculate("__import__('os').system('id')")

    with pytest.raises(ValueError, match="safety limit"):
        calculate("10 ** 1001")


def test_calculator_tool_returns_no_fabricated_sources() -> None:
    result = asyncio.run(CalculatorTool().call("10 / 4", precision=2))
    assert result.content == "2.5"
    assert result.sources == []


def test_current_time_converts_supplied_iso_and_applies_offset() -> None:
    result = asyncio.run(
        CurrentTimeTool().call(
            "convert time",
            timezone_name="America/New_York",
            at_iso="2025-01-01T12:00:00Z",
            add_days=1,
        )
    )
    assert result.content.startswith("2025-01-02T07:00:00-05:00")


def test_webpage_extraction_preserves_title_date_and_main_text() -> None:
    html = """
    <html><head><title>Example Article</title>
    <meta property="article:published_time" content="2025-02-03T10:00:00Z"></head>
    <body><article><h1>Example Article</h1><p>This is the material article content with enough useful words for extraction.</p></article></body></html>
    """
    text, metadata = _extract(html, "https://example.com/article", 10_000)
    assert "material article content" in text
    assert metadata["title"] == "Example Article"
    assert metadata["published_at"] == "2025-02-03T10:00:00Z"


def test_url_guard_rejects_private_network_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(ValueError, match="Private"):
        asyncio.run(validate_public_url("https://internal.example/path"))


def test_web_search_tries_ddgs_once_then_permanently_uses_tavily(monkeypatch) -> None:
    calls = {"ddgs": 0, "tavily": 0}

    def empty_ddgs(query: str, max_results: int):
        calls["ddgs"] += 1
        return []

    def successful_tavily(query: str, max_results: int, api_key: str):
        calls["tavily"] += 1
        return [{"title": "Primary", "url": "https://example.com", "content": "Evidence"}]

    monkeypatch.setenv("TAVILY_API_KEY", "test")
    monkeypatch.setattr(web_search_module, "_duckduckgo", empty_ddgs)
    monkeypatch.setattr(web_search_module, "_tavily", successful_tavily)

    tool = WebSearchTool()
    result = asyncio.run(tool.call_with_retry("query", max_retries=2))

    assert result.ok
    assert calls == {"ddgs": 1, "tavily": 1}
    assert tool.search_backend == "tavily"
    assert result.sources[0]["search_provider"] == "tavily"
