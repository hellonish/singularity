"""
ArxivTool — searches arXiv using the `arxiv` Python SDK.

credibility_base: 0.95 if journal_ref is populated (published), 0.88 for preprints.
Supports recency filtering via `max_age_years` kwarg.
"""
import asyncio
from datetime import datetime, timezone, timedelta

from .base import ToolBase, ToolResult


def _search(query: str, max_results: int, max_age_years: float | None) -> list[dict]:
    import arxiv

    cutoff = None
    if max_age_years:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=365 * max_age_years)

    results = []
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    for paper in arxiv.Client().results(search):
        if cutoff and paper.published and paper.published < cutoff:
            continue
        results.append({
            "title":    paper.title,
            "authors":  [str(a) for a in paper.authors],
            "abstract": paper.summary[:500],
            "url":      paper.entry_id,
            "pdf_url":  paper.pdf_url,
            "date":     paper.published.strftime("%Y-%m-%d") if paper.published else None,
            "journal":  paper.journal_ref,
            "arxiv_id": paper.entry_id.split("/")[-1],
        })
    return results


class ArxivTool(ToolBase):
    name = "arxiv"

    async def call(
        self,
        query: str,
        max_results: int = 10,
        max_age_years: float | None = None,
        **kwargs,
    ) -> ToolResult:
        raw = await asyncio.to_thread(_search, query, max_results, max_age_years)

        if not raw:
            raise ValueError("No arXiv results found")

        sources = [
            {
                "title":            r["title"],
                "url":              r["url"],
                "snippet":          r["abstract"],
                "date":             r["date"],
                "authors":          r["authors"],
                "source_type":      "academic",
                "credibility_base": 0.95 if r.get("journal") else 0.88,
                "metadata": {
                    "arxiv_id": r["arxiv_id"],
                    "pdf_url":  r["pdf_url"],
                    "journal":  r.get("journal"),
                },
            }
            for r in raw
        ]
        avg_cred = sum(s["credibility_base"] for s in sources) / len(sources)
        content  = "\n\n".join(
            f"[{s['title']}] {', '.join(s['authors'][:3])}\n{s['snippet']}"
            for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=avg_cred, raw=raw)
