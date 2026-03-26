"""
academic_search — queries arXiv and Semantic Scholar in parallel, deduplicates
by title prefix, and returns a merged source list.
"""
import asyncio

from tools.arxiv_api import ArxivTool
from tools.semantic_scholar import SemanticScholarTool
from models import NodeStatus
from ..base import BaseRetrievalSkill


class AcademicSearchSkill(BaseRetrievalSkill):
    name   = "academic_search"
    min_ok = 2

    async def run(self, node, ctx, client, registry):
        half = max(self._depth_n(node) // 2, 3)

        arxiv_res, s2_res = await asyncio.gather(
            ArxivTool().call_with_retry(node.description, max_results=half),
            SemanticScholarTool().call_with_retry(node.description, max_results=half),
            return_exceptions=True,
        )

        sources: list[dict] = []
        seen: set[str] = set()

        for res in (arxiv_res, s2_res):
            if isinstance(res, Exception) or not res.ok:
                continue
            for src in res.sources:
                key = src.get("title", "")[:50].lower()
                if key not in seen:
                    seen.add(key)
                    sources.append(src)

        if not sources:
            errors = [
                getattr(r, "error", str(r))
                for r in (arxiv_res, s2_res)
                if isinstance(r, Exception) or (hasattr(r, "ok") and not r.ok)
            ]
            return self._fail(node, "; ".join(errors) or "No academic results found")

        self._register_all(sources, node, ctx)

        fallback = any(
            isinstance(r, Exception) or (hasattr(r, "ok") and not r.ok)
            for r in (arxiv_res, s2_res)
        )
        return self._build_output(
            sources, node,
            coverage_notes=f"{len(sources)} paper(s) from arXiv + Semantic Scholar",
            fallback_used=fallback,
        )
