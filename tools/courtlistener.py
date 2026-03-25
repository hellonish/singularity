"""
CourtListenerTool — searches US case law via CourtListener REST API.

Endpoint: https://www.courtlistener.com/api/rest/v4/search/
Free, no authentication required for basic search.
credibility_base: 0.95 (official court records).
"""
import aiohttp

from .base import ToolBase, ToolResult, ssl_ctx

_BASE_URL = "https://www.courtlistener.com/api/rest/v4/search/"


class CourtListenerTool(ToolBase):
    name = "courtlistener"

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        params = {"q": query, "type": "o", "page_size": max_results}

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx())) as session:
            async with session.get(_BASE_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

        results = data.get("results", [])
        if not results:
            raise ValueError("No CourtListener results found")

        sources = [
            {
                "title":            r.get("caseName", r.get("case_name", "")),
                "url":              f"https://www.courtlistener.com{r.get('absolute_url', '')}",
                "snippet":          (r.get("snippet") or r.get("summary") or "")[:300],
                "date":             r.get("dateFiled") or r.get("date_filed"),
                "source_type":      "legal",
                "credibility_base": 0.95,
                "metadata": {
                    "court":      r.get("court", r.get("court_id", "")),
                    "citation":   r.get("citation", [r.get("caseName", "")]),
                    "status":     r.get("status", ""),
                    "docket_num": r.get("docketNumber", ""),
                },
            }
            for r in results
        ]
        content = "\n\n".join(
            f"[{s['title']}] {s['metadata']['court']} ({s['date']})\n{s['snippet']}"
            for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=0.95, raw=data)
