"""General public-web search through DuckDuckGo with optional Tavily fallback."""
from __future__ import annotations

import asyncio
import os

from .base import ToolBase, ToolResult

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

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        try:
            raw = await asyncio.to_thread(_duckduckgo, query, max_results)
        except Exception as primary_error:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                raise primary_error
            raw = await asyncio.to_thread(_tavily, query, max_results, api_key)
        if not raw:
            raise ValueError("No search results returned")
        sources = []
        for item in raw[:max_results]:
            url = item.get("href") or item.get("url", "")
            sources.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": (item.get("body") or item.get("content", ""))[:500],
                "date": item.get("published") or item.get("date"),
                "source_type": "web_search",
                "credibility_base": _credibility(url),
            })
        content = "\n\n".join(
            f"[{source['title']}] ({source['url']})\n{source['snippet']}" for source in sources
        )
        credibility = sum(source["credibility_base"] for source in sources) / len(sources)
        return ToolResult(content=content, sources=sources, credibility_base=credibility, raw=raw)
