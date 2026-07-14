"""General public-web search through DuckDuckGo with optional Tavily fallback."""
from __future__ import annotations

import asyncio
import os

from .base import ToolBase, ToolResult
from engine.chat.retry import PermanentActionError

_TRUSTED = (".gov", ".edu", ".gov.uk", ".gov.au", ".gc.ca", ".europa.eu")


def _credibility(url: str) -> float:
    return 0.85 if any(domain in url for domain in _TRUSTED) else 0.75


def _duckduckgo(query: str, max_results: int) -> list[dict]:
    from ddgs import DDGS

    return list(DDGS().text(query, max_results=max_results))


def _tavily(query: str, max_results: int, api_key: str) -> list[dict]:
    from tavily import TavilyClient

    return TavilyClient(api_key=api_key).search(query, max_results=max_results).get("results", [])


class WebSearchTool(ToolBase):
    name = "web_search"
    description = "Search the public web and return result titles, URLs, dates, and snippets."
    skill_ids = ("general_web_research", "source_discovery")

    def __init__(self) -> None:
        # A ToolBase retry reuses the same instance. Once DDGS fails or returns
        # nothing, every later attempt in this logical action is Tavily-only.
        self._ddgs_disabled = False

    @property
    def search_backend(self) -> str:
        return "tavily" if self._ddgs_disabled else "ddgs"

    async def call(
        self,
        query: str,
        max_results: int = 10,
        search_backend: str = "auto",
        **kwargs,
    ) -> ToolResult:
        backend = "tavily" if search_backend == "tavily" or self._ddgs_disabled else "ddgs"
        raw: list[dict]
        if backend == "ddgs":
            try:
                raw = await asyncio.to_thread(_duckduckgo, query, max_results)
            except Exception:
                raw = []
            if not raw:
                self._ddgs_disabled = True
                backend = "tavily"
        if backend == "tavily":
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                raise PermanentActionError("Tavily fallback is unavailable because TAVILY_API_KEY is not configured")
            raw = await asyncio.to_thread(_tavily, query, max_results, api_key)
        if not raw:
            raise RuntimeError(f"No search results returned by {backend}")
        sources = []
        for item in raw[:max_results]:
            url = item.get("href") or item.get("url", "")
            sources.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": (item.get("body") or item.get("content", ""))[:500],
                "date": item.get("published") or item.get("date"),
                "source_type": "web_search",
                "search_provider": backend,
                "credibility_base": _credibility(url),
            })
        content = "\n\n".join(
            f"[{source['title']}] ({source['url']})\n{source['snippet']}" for source in sources
        )
        credibility = sum(source["credibility_base"] for source in sources) / len(sources)
        return ToolResult(content=content, sources=sources, credibility_base=credibility, raw=raw)
