"""
SemanticScholarTool — searches the Semantic Scholar Graph API (free).

Endpoint: https://api.semanticscholar.org/graph/v1/paper/search
Rate limits: 100 req/5 min unauthenticated, 1 req/sec recommended.
credibility_base: 0.90 base; boosted to 0.95 if citationCount > 50.
"""
import asyncio

import aiohttp

from .base import ToolBase, ToolResult, ssl_ctx

_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS   = "title,authors,year,abstract,citationCount,openAccessPdf,externalIds"


async def _fetch(query: str, limit: int) -> list[dict]:
    params = {"query": query, "limit": limit, "fields": _FIELDS}
    for attempt in range(3):
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx())) as session:
            async with session.get(_BASE_URL, params=params) as resp:
                if resp.status == 429:
                    await asyncio.sleep(10 * (attempt + 1))   # 10s, 20s, 30s on rate limit
                    continue
                resp.raise_for_status()
                data = await resp.json()
        return data.get("data", [])
    raise RuntimeError("Semantic Scholar rate limit exceeded — try again later")


class SemanticScholarTool(ToolBase):
    name = "semantic_scholar"

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        raw = await _fetch(query, max_results)

        if not raw:
            raise ValueError("No Semantic Scholar results found")

        sources = []
        for paper in raw:
            pdf  = paper.get("openAccessPdf") or {}
            doi  = (paper.get("externalIds") or {}).get("DOI", "")
            url  = pdf.get("url") or (f"https://doi.org/{doi}" if doi else "")
            cred = 0.95 if (paper.get("citationCount") or 0) > 50 else 0.90
            sources.append({
                "title":            paper.get("title", ""),
                "url":              url or f"https://www.semanticscholar.org/paper/{paper.get('paperId','')}",
                "snippet":          (paper.get("abstract") or "")[:400],
                "date":             str(paper["year"]) if paper.get("year") else None,
                "authors":          [a.get("name", "") for a in (paper.get("authors") or [])],
                "source_type":      "academic",
                "credibility_base": cred,
                "metadata": {
                    "paper_id":      paper.get("paperId"),
                    "citation_count": paper.get("citationCount", 0),
                    "doi":           doi,
                    "open_access":   bool(pdf.get("url")),
                },
            })

        avg_cred = sum(s["credibility_base"] for s in sources) / len(sources)
        content  = "\n\n".join(
            f"[{s['title']}] ({s['metadata']['citation_count']} citations)\n{s['snippet']}"
            for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=avg_cred, raw=raw)
