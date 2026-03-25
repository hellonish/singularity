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

from .base import ToolBase, ToolResult

_NIST_URL  = "https://csrc.nist.gov/CSRC/media/Publications/sp/800-53/rev-5/final/documents"
_NIST_SEARCH = "https://csrc.nist.gov/publications/search"
_IEEE_URL  = "https://ieeexploreapi.ieee.org/api/v1/search/articles"


async def _nist_search(query: str, max_results: int) -> list[dict]:
    # NIST CSRC publication search (scrapes the public search endpoint)
    params = {"SearchText": query, "SearchAreaNumber": "0", "SearchAreaName": "all"}
    async with aiohttp.ClientSession() as session:
        async with session.get(_NIST_SEARCH, params=params) as resp:
            resp.raise_for_status()
            text = await resp.text()

    # Parse very simple result extraction — titles and URLs from the response
    import re
    results = []
    for match in re.finditer(
        r'href="(/publications/detail/[^"]+)"[^>]*>([^<]+)</a>', text
    ):
        url, title = match.groups()
        results.append({
            "title":    title.strip(),
            "url":      f"https://csrc.nist.gov{url}",
            "source":   "NIST",
        })
        if len(results) >= max_results:
            break
    return results


async def _ieee_search(query: str, max_results: int, api_key: str) -> list[dict]:
    params = {
        "querytext":  query,
        "max_records": max_results,
        "apikey":     api_key,
    }
    async with aiohttp.ClientSession() as session:
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
