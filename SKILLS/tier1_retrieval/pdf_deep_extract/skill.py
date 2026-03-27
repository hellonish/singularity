"""
pdf_deep_extract — fetches and chunks PDFs relevant to the query.

When a URL is already present in the description it is used directly.
Otherwise a DuckDuckGo search scoped to PDF files finds candidate URLs,
and the first successfully extracted PDF is returned as a ToolResult.
"""
import asyncio
import re

from tools.pdf_reader import PdfReaderTool
from tools.base import ToolResult
from ..base import BaseRetrievalSkill

_URL_RE = re.compile(r"https?://\S+\.pdf\b", re.I)
_ANY_URL_RE = re.compile(r"https?://\S+", re.I)


def _ddg_pdf_search(query: str, max_results: int = 6) -> list[str]:
    """
    Uses DuckDuckGo to find PDF URLs for `query`.
    Prefers results whose href ends in .pdf; falls back to any URL containing
    'pdf' in the path (common for arXiv, ResearchGate, etc.).
    """
    from ddgs import DDGS
    results = DDGS().text(f"{query} filetype:pdf", max_results=max_results * 3)
    urls: list[str] = []
    for r in results:
        href = r.get("href", "") or r.get("url", "")
        if not href:
            continue
        if href.lower().endswith(".pdf") or "pdf" in href.lower():
            urls.append(href)
        if len(urls) >= max_results:
            break
    return urls


class PdfDeepExtractSkill(BaseRetrievalSkill):
    name   = "pdf_deep_extract"
    min_ok = 1

    async def _fetch(self, node, query=None):
        """
        Phase 5 fanout path.  For each call:
        1. If the query/description contains a direct .pdf URL, use it.
        2. Otherwise run a DDG 'filetype:pdf' search to discover candidate URLs,
           then attempt extraction on each until one succeeds.

        Args:
            node:  PlanNode (used for metadata; description is the fallback query).
            query: Sub-query string from the retrieval planner (overrides description).

        Returns:
            ToolResult from the first successfully extracted PDF.
        """
        description = query or node.description

        # Direct URL in the text — use immediately
        direct = _URL_RE.findall(description) or _ANY_URL_RE.findall(description)
        if direct:
            return await PdfReaderTool().call_with_retry(
                query=description, url=direct[0].rstrip(".,)")
            )

        # No URL — discover PDFs via DDG
        candidate_urls = await asyncio.to_thread(_ddg_pdf_search, description)
        if not candidate_urls:
            return ToolResult.failure(f"pdf_deep_extract: no PDF URLs found for query '{description[:80]}'")

        for url in candidate_urls:
            result = await PdfReaderTool().call_with_retry(query=description, url=url)
            if result.ok and result.sources:
                return result

        return ToolResult.failure(
            f"pdf_deep_extract: PDF extraction failed for all {len(candidate_urls)} candidate URLs"
        )
