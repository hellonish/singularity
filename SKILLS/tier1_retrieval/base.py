"""
BaseRetrievalSkill — shared pattern for all 18 tier-1 retrieval skills.

Subclass this and implement _fetch(node, query) → ToolResult.
For multi-tool skills (academic, clinical, financial) override run() directly.

Phase 5 additions:
  - run_fanout(): execute Q(s) queries per skill and ingest all results to Qdrant
  - _ingest_to_qdrant(): chunk + embed + upsert a source to the run's collection
"""
import re
from typing import Any

from skills.base import SkillBase
from models import NodeStatus, PlanNode


# ---------------------------------------------------------------------------
# Domain credibility scoring (Issue 7)
# ---------------------------------------------------------------------------

_HIGH_CREDIBILITY_DOMAINS: tuple[str, ...] = (
    ".gov", ".gov.uk", ".gov.au", ".gov.ca",
    ".edu", ".ac.uk", ".ac.jp", ".edu.au",
    "reuters.com", "apnews.com",
    "bbc.com", "bbc.co.uk",
    "nature.com", "science.org", "nejm.org", "thelancet.com",
    "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov",
    "who.int", "un.org", "worldbank.org", "imf.org", "oecd.org", "europa.eu",
    "sciencedirect.com", "springer.com", "jstor.org", "arxiv.org",
)

_LOW_CREDIBILITY_DOMAINS: tuple[str, ...] = (
    "dailymail.co.uk", "thesun.co.uk",
    "infowars.com", "breitbart.com", "naturalnews.com",
    "beforeitsnews.com", "globalresearch.ca", "zerohedge.com",
)

_CREDIBILITY_BOOST   = 0.15   # added for high-credibility domain hits
_CREDIBILITY_PENALTY = 0.20   # subtracted for low-credibility domain hits


def _adjust_credibility(url: str, base: float) -> float:
    """Apply domain-based credibility adjustment. Clamped to [0.0, 1.0]."""
    if not url:
        return base
    url_lower = url.lower()
    for domain in _HIGH_CREDIBILITY_DOMAINS:
        if domain in url_lower:
            return min(1.0, base + _CREDIBILITY_BOOST)
    for domain in _LOW_CREDIBILITY_DOMAINS:
        if domain in url_lower:
            return max(0.0, base - _CREDIBILITY_PENALTY)
    return base


class BaseRetrievalSkill(SkillBase):
    # Minimum sources required for NodeStatus.OK (vs PARTIAL)
    min_ok: int = 2

    # ---------------------------------------------------------------------------
    # Override in subclass
    # ---------------------------------------------------------------------------

    async def _fetch(self, node: PlanNode, query: str | None = None):
        """
        Call the tool and return a ToolResult.
        `query` overrides node.description when provided (used during fanout).
        Raise on hard error.
        """
        raise NotImplementedError

    # ---------------------------------------------------------------------------
    # Phase 5: multi-query fanout + Qdrant ingestion
    # ---------------------------------------------------------------------------

    async def run_fanout(
        self,
        queries: list[str],
        run_id: str,
        collection_name: str,
        node: PlanNode,
        ctx,
        vs=None,
    ) -> dict[str, Any]:
        """
        Execute all Q queries for this skill, ingest results to Qdrant.
        Returns a summary dict (not stored in ctx.results — Qdrant is the store).
        """
        import asyncio
        from vector_store.client import VectorStoreClient

        if vs is None:
            vs = VectorStoreClient()
        total_chunks = 0
        total_sources = 0
        all_sources: list[dict] = []

        # Run all queries concurrently
        async def _run_one(q: str):
            nonlocal total_chunks, total_sources
            try:
                result = await self._fetch(node, query=q)
            except Exception:
                return
            if not result or not getattr(result, "ok", False):
                return
            for src in result.sources:
                text = src.get("content", "") or src.get("snippet", "") or src.get("abstract", "")
                if not text:
                    continue
                base_cred = src.get("credibility_base", 0.7)
                adjusted_cred = _adjust_credibility(src.get("url", ""), base_cred)
                chunks = vs.ingest_text(
                    collection_name=collection_name,
                    text=text,
                    run_id=run_id,
                    source_url=src.get("url", ""),
                    source_title=src.get("title", "Unknown"),
                    credibility=adjusted_cred,
                    skill=self.name,
                    query=q,
                )
                total_chunks += len(chunks)
                total_sources += 1
                all_sources.append(src)

        await asyncio.gather(*[_run_one(q) for q in queries])

        # Register citations
        cit_reg = getattr(ctx, "citation_registry", None)
        if cit_reg is not None:
            for src in all_sources:
                cid = cit_reg.register(src, self.name, node.output_slot)
                src["citation_id"] = cid

        return {
            "skill":         self.name,
            "queries_run":   len(queries),
            "sources_found": total_sources,
            "chunks_stored": total_chunks,
        }

    # ---------------------------------------------------------------------------
    # Shared run() logic (legacy DAG path — still used for --depth runs)
    # ---------------------------------------------------------------------------

    async def run(self, node, ctx, client, registry):
        try:
            result = await self._fetch(node, query=None)
        except Exception as exc:
            return self._fail(node, str(exc))

        if not result.ok:
            return self._fail(node, result.error)

        sources = list(result.sources)

        # Register every source in the citation registry
        cit_reg = getattr(ctx, "citation_registry", None)
        if cit_reg is not None:
            for src in sources:
                cid = cit_reg.register(src, self.name, node.output_slot)
                src["citation_id"] = cid

        n      = len(sources)
        status = (NodeStatus.OK      if n >= self.min_ok else
                  NodeStatus.PARTIAL if n > 0           else
                  NodeStatus.FAILED)
        avg_cred = (sum(s.get("credibility_base", 0.75) for s in sources) / n
                    if n else 0.0)

        return {
            "skill_name":     self.name,
            "sources":        sources,
            "query_used":     node.description,
            "result_count":   n,
            "coverage_notes": self._notes(n),
            "fallback_used":  False,
        }, status, avg_cred

    # ---------------------------------------------------------------------------
    # Helpers available to all subclasses
    # ---------------------------------------------------------------------------

    def _fail(self, node: PlanNode, error: str | None):
        return {
            "skill_name":     self.name,
            "sources":        [],
            "query_used":     node.description,
            "result_count":   0,
            "coverage_notes": f"FAILED: {error}",
            "fallback_used":  False,
        }, NodeStatus.FAILED, 0.0

    def _notes(self, n: int) -> str:
        if n == 0:
            return "No results found"
        if n < self.min_ok:
            return f"{n} result(s) — below minimum ({self.min_ok} required for OK)"
        return f"{n} result(s) found"

    def _to_query(self, description: str, max_words: int = 8) -> str:
        """Extract a concise keyword query from a verbose node description.

        Strips instruction-style prefixes ("Search X for examples of ...") and
        returns the core topic words, capped at max_words.
        """
        m = re.search(
            r'\b(?:for(?:\s+examples?\s+of)?|about|on|of|highlighting|covering|related\s+to)\s+(.+)',
            description, re.IGNORECASE,
        )
        topic = m.group(1) if m else description
        # Cut at first comma/semicolon/colon to drop "such as ..." clauses
        topic = re.sub(r'[,;:].*', '', topic).strip()
        words = topic.split()
        return " ".join(words[:max_words])

    def _depth_n(self, node: PlanNode, ctx=None, default: int = 10) -> int:
        """Map depth → max_results. Node-level override wins; ctx.depth is the global fallback."""
        _MAP = {"shallow": 5, "standard": 10, "deep": 20}
        key = node.depth_override or (getattr(ctx, "depth", None)) or ""
        return _MAP.get(key, default)

    def _register_all(self, sources: list[dict], node: PlanNode, ctx) -> list[dict]:
        """Register a list of sources and mutate each with citation_id. Returns sources."""
        cit_reg = getattr(ctx, "citation_registry", None)
        if cit_reg is not None:
            for src in sources:
                cid = cit_reg.register(src, self.name, node.output_slot)
                src["citation_id"] = cid
        return sources

    def _build_output(
        self,
        sources: list[dict],
        node: PlanNode,
        coverage_notes: str | None = None,
        fallback_used: bool = False,
    ) -> tuple[dict, NodeStatus, float]:
        n = len(sources)
        status = (NodeStatus.OK      if n >= self.min_ok else
                  NodeStatus.PARTIAL if n > 0           else
                  NodeStatus.FAILED)
        avg_cred = (sum(s.get("credibility_base", 0.75) for s in sources) / n
                    if n else 0.0)
        return {
            "skill_name":     self.name,
            "sources":        sources,
            "query_used":     node.description,
            "result_count":   n,
            "coverage_notes": coverage_notes or self._notes(n),
            "fallback_used":  fallback_used,
        }, status, avg_cred
