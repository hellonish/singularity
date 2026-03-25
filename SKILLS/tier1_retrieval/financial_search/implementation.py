"""
financial_search — SEC EDGAR filings (credibility 1.0) + financial web news.
EDGAR is tried first; web search is always run as supplement.
"""
import asyncio

from tools.sec_edgar import SecEdgarTool
from tools.web_fetch import WebFetchTool
from .._base import BaseRetrievalSkill

_FIN_SITES = "bloomberg.com OR ft.com OR reuters.com OR wsj.com OR cnbc.com"


class FinancialSearchSkill(BaseRetrievalSkill):
    name   = "financial_search"
    min_ok = 2

    async def run(self, node, ctx, client, registry):
        half = max(self._depth_n(node) // 2, 3)

        edgar_res, web_res = await asyncio.gather(
            SecEdgarTool().call_with_retry(node.description, max_results=half),
            WebFetchTool().call_with_retry(
                f"{node.description} financial ({_FIN_SITES})", max_results=half
            ),
            return_exceptions=True,
        )

        # EDGAR sources go first (higher credibility)
        sources: list[dict] = []
        for res in (edgar_res, web_res):
            if not isinstance(res, Exception) and res.ok:
                sources.extend(res.sources)

        if not sources:
            return self._fail(node, "No financial sources found")

        self._register_all(sources, node, ctx)

        return self._build_output(
            sources, node,
            coverage_notes=f"{len(sources)} financial source(s) from SEC EDGAR + web",
            fallback_used=isinstance(edgar_res, Exception) or (hasattr(edgar_res, "ok") and not edgar_res.ok),
        )
