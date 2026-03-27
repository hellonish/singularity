"""
WebFetchTool — general web search.

Primary:  DuckDuckGo (free, no key)
Fallback: Tavily      (requires TAVILY_API_KEY env var)

credibility_base: 0.85 for .gov/.edu domains, 0.75 for everything else.
"""
import asyncio
import os

from .base import ToolBase, ToolResult

# Domains considered authoritative for credibility boost
_TRUSTED = (".gov", ".edu", ".gov.uk", ".gov.au", ".gc.ca", ".europa.eu")


def _cred(url: str) -> float:
    return 0.85 if any(p in url for p in _TRUSTED) else 0.75


# ---------------------------------------------------------------------------
# Sync wrappers (run in thread pool via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _ddg(query: str, max_results: int) -> list[dict]:
    from ddgs import DDGS
    return list(DDGS().text(query, max_results=max_results))


def _tavily(query: str, max_results: int, api_key: str) -> list[dict]:
    from tavily import TavilyClient
    resp = TavilyClient(api_key=api_key).search(query, max_results=max_results)
    return resp.get("results", [])


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

class WebFetchTool(ToolBase):
    name = "web_fetch"

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        try:
            raw = await asyncio.to_thread(_ddg, query, max_results)
        except Exception as ddg_exc:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                raise ddg_exc
            raw = await asyncio.to_thread(_tavily, query, max_results, api_key)

        if not raw:
            raise ValueError("No results returned")

        sources = [
            {
                "title":            r.get("title", ""),
                "url":              r.get("href") or r.get("url", ""),
                "snippet":          (r.get("body") or r.get("content", ""))[:300],
                "date":             r.get("published") or r.get("date"),
                "source_type":      "web",
                "credibility_base": _cred(r.get("href") or r.get("url", "")),
            }
            for r in raw
        ]
        avg_cred = sum(s["credibility_base"] for s in sources) / len(sources)
        content  = "\n\n".join(
            f"[{s['title']}] ({s['url']})\n{s['snippet']}" for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=avg_cred, raw=raw)
