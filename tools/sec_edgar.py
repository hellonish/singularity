"""
SecEdgarTool — searches SEC EDGAR full-text search REST API.

Endpoint: https://efts.sec.gov/LATEST/search-index?q={query}
Free, no authentication required.
credibility_base: 1.0 (official regulatory filings).
"""
import aiohttp

from .base import ToolBase, ToolResult

_SEARCH_URL  = "https://efts.sec.gov/LATEST/search-index"
_FILING_BASE = "https://www.sec.gov"


class SecEdgarTool(ToolBase):
    name = "sec_edgar"

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        params = {"q": f'"{query}"', "dateRange": "custom", "forms": "10-K,10-Q,8-K"}

        async with aiohttp.ClientSession() as session:
            async with session.get(_SEARCH_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

        hits = data.get("hits", {}).get("hits", [])[:max_results]
        if not hits:
            raise ValueError("No SEC EDGAR results found")

        sources = []
        for hit in hits:
            src  = hit.get("_source", {})
            url  = f"{_FILING_BASE}{src.get('file_date', '')}"
            # Build a usable URL from entity_name + accession_number when available
            acc  = src.get("period_of_report", "") or ""
            url  = (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                    f"&company={src.get('entity_name','')}&type={src.get('form_type','')}"
                    f"&dateb=&owner=include&count=10")
            sources.append({
                "title":            f"{src.get('entity_name', 'Unknown')} — {src.get('form_type', '')} ({src.get('file_date', '')})",
                "url":              url,
                "snippet":          (src.get("period_of_report") or "")[:300],
                "date":             src.get("file_date"),
                "source_type":      "financial",
                "credibility_base": 1.0,
                "metadata": {
                    "company":     src.get("entity_name", ""),
                    "form_type":   src.get("form_type", ""),
                    "period":      src.get("period_of_report", ""),
                    "accession":   src.get("accession_no", ""),
                    "cik":         src.get("entity_id", ""),
                },
            })

        content = "\n\n".join(
            f"[{s['title']}]\n{s['snippet']}" for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=1.0, raw=data)
