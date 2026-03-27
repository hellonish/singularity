"""
academic_search — queries arXiv and Semantic Scholar in parallel, deduplicates
by title prefix, and returns a merged source list.

Both run() (legacy DAG path) and _fetch() (Phase 5 run_fanout path) delegate to
_query(), keeping deduplication and error handling in one place.
"""
import asyncio

from tools.arxiv_api import ArxivTool
from tools.semantic_scholar import SemanticScholarTool
from tools.base import ToolResult
from models import NodeStatus
from ..base import BaseRetrievalSkill


class AcademicSearchSkill(BaseRetrievalSkill):
    name   = "academic_search"
    min_ok = 2

    async def _fetch(self, node, query=None):
        """
        Called by BaseRetrievalSkill.run_fanout() for each sub-query in Phase 5.
        Fans out to ArxivTool + SemanticScholarTool in parallel, deduplicates by
        title prefix, and returns a merged ToolResult.

        Args:
            node:  PlanNode carrying depth / output_slot metadata.
            query: Override query string; falls back to node.description.

        Returns:
            ToolResult with merged sources from both academic indexes.
        """
        q    = query or node.description
        half = max(self._depth_n(node) // 2, 3)
        return await self._query(q, half)

    async def run(self, node, ctx, client, registry):
        """
        Legacy DAG path (--depth runs). Calls _query() and wraps the result in
        the expected (output_dict, NodeStatus, credibility) tuple.
        """
        half = max(self._depth_n(node) // 2, 3)
        result = await self._query(node.description, half)

        if not result.ok:
            return self._fail(node, result.error)

        sources = list(result.sources)
        self._register_all(sources, node, ctx)
        fallback = result.raw.get("partial", False) if isinstance(result.raw, dict) else False
        return self._build_output(
            sources, node,
            coverage_notes=f"{len(sources)} paper(s) from arXiv + Semantic Scholar",
            fallback_used=fallback,
        )

    async def _query(self, query: str, half: int) -> ToolResult:
        """
        Runs ArxivTool and SemanticScholarTool in parallel for `query`, requesting
        `half` results from each.  Deduplicates by 50-char lowercased title prefix.
        Returns a ToolResult with the merged source list; sets error if both fail.
        """
        arxiv_res, s2_res = await asyncio.gather(
            ArxivTool().call_with_retry(query, max_results=half),
            SemanticScholarTool().call_with_retry(query, max_results=half),
            return_exceptions=True,
        )

        sources: list[dict] = []
        seen:    set[str]   = set()

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
            return ToolResult.failure("; ".join(errors) or "No academic results found")

        partial = any(
            isinstance(r, Exception) or (hasattr(r, "ok") and not r.ok)
            for r in (arxiv_res, s2_res)
        )
        avg_cred = sum(s["credibility_base"] for s in sources) / len(sources)
        content  = "\n\n".join(
            f"[{s['title']}]\n{s.get('snippet', '')}" for s in sources[:5]
        )
        return ToolResult(
            content=content,
            sources=sources,
            credibility_base=avg_cred,
            raw={"partial": partial},
        )
