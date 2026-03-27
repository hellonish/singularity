"""
StandardsFetchTool — searches NIST CSRC publications and IEEE Xplore.

NIST: free, no auth.
IEEE Xplore: free tier requires IEEE_API_KEY env var (100 req/day without key is unreliable).
credibility_base: 1.0 (official standards bodies).
"""
import asyncio
import os
from urllib.parse import quote

import aiohttp

from .base import ToolBase, ToolResult, ssl_ctx

_NIST_BASE = "https://csrc.nist.gov"
_IEEE_URL  = "https://ieeexploreapi.ieee.org/api/v1/search/articles"


def _nist_search_sync(query: str, max_results: int) -> list[dict]:
    """DDG site:csrc.nist.gov search — NIST CSRC is a JS-rendered SPA with no public JSON API."""
    from ddgs import DDGS
    results = []
    for r in DDGS().text(f"site:csrc.nist.gov {query}", max_results=max_results):
        results.append({
            "title":  r.get("title", ""),
            "url":    r.get("href") or r.get("url", ""),
            "source": "NIST",
        })
    return results


async def _nist_search(query: str, max_results: int) -> list[dict]:
    return await asyncio.to_thread(_nist_search_sync, query, max_results)


async def _ieee_search(query: str, max_results: int, api_key: str) -> list[dict]:
    params = {
        "querytext":  query,
        "max_records": max_results,
        "apikey":     api_key,
    }
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx())) as session:
        async with session.get(_IEEE_URL, params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()

    results = []
    for article in data.get("articles", []):
        results.append({
            "title":      article.get("title", ""),
            "url":        article.get("pdf_url") or article.get("abstract_url", ""),
            "date":       article.get("publication_year"),
            "standard":   article.get("standard_number", ""),
            "publisher":  article.get("publisher", "IEEE"),
            "source":     "IEEE",
        })
    return results


class StandardsFetchTool(ToolBase):
    name = "standards_fetch"

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        nist_task = asyncio.create_task(_nist_search(query, max_results // 2 + 1))

        ieee_key = os.getenv("IEEE_API_KEY")
        ieee_task = (
            asyncio.create_task(_ieee_search(query, max_results // 2 + 1, ieee_key))
            if ieee_key else None
        )

        nist_results = await nist_task
        ieee_results = await ieee_task if ieee_task else []

        raw_all = nist_results + ieee_results
        if not raw_all:
            raise ValueError("No standards found")

        sources = [
            {
                "title":            r["title"],
                "url":              r["url"],
                "snippet":          r.get("standard", r.get("publisher", "")),
                "date":             str(r["date"]) if r.get("date") else None,
                "source_type":      "standard",
                "credibility_base": 1.0,
                "metadata": {
                    "issuing_body":    r.get("source", "NIST"),
                    "standard_number": r.get("standard", ""),
                },
            }
            for r in raw_all[:max_results]
        ]
        content = "\n\n".join(
            f"[{s['title']}] {s['metadata']['issuing_body']}" for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=1.0, raw=raw_all)
