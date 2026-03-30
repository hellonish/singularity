"""
BaseRetrievalSkill — shared pattern for all 18 tier-1 retrieval skills.

Subclass this and implement _fetch(node, query) → ToolResult.
For multi-tool skills (academic, clinical, financial) override run() directly.

Phase 5 additions:
  - run_fanout(): execute Q(s) queries per skill and ingest all results to Qdrant
  - _ingest_to_qdrant(): chunk + embed + upsert a source to the run's collection
"""
import logging
import re
from typing import Any

from skills.base import SkillBase
from models import NodeStatus, PlanNode

logger = logging.getLogger(__name__)


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
        original_query: str | None = None,
        gate_client=None,
    ) -> dict[str, Any]:
        """
        Execute all Q queries for this skill, gate results, ingest to Qdrant.
        Returns a summary dict (not stored in ctx.results — Qdrant is the store).

        2-pass source gate (active when original_query and gate_client are set):
          Pass 1 — local embedding cosine similarity filter (zero LLM cost).
          Pass 2 — aggregate Grok call across all Pass-1 survivors for the skill
                   (one call total, not one per query).
        Fallback at every stage: never silently empty the source pool.
        """
        import asyncio
        from vector_store.client import VectorStoreClient

        if vs is None:
            vs = VectorStoreClient()

        # ------------------------------------------------------------------
        # Step 1: Fetch all queries in parallel; run Pass 1 on each batch
        # ------------------------------------------------------------------

        async def _fetch_and_filter(q: str) -> list[tuple[dict, str]]:
            """Returns (source_dict, sub_query) pairs surviving Pass 1."""
            try:
                result = await self._fetch(node, query=q)
            except Exception as exc:
                logger.warning("[%s] fetch failed for query %r: %s", self.name, q, exc)
                return []
            if not result or not getattr(result, "ok", False):
                return []

            sources = [
                s for s in result.sources
                if s.get("content") or s.get("snippet") or s.get("abstract")
            ]
            if not sources:
                return []

            if original_query:
                from agents.source_gate import pass1_filter
                sources = pass1_filter(sources, original_query)

            return [(src, q) for src in sources]

        batches = await asyncio.gather(*[_fetch_and_filter(q) for q in queries])
        all_survivors: list[tuple[dict, str]] = [
            item for batch in batches for item in batch
        ]

        # ------------------------------------------------------------------
        # Step 2: Pass 2 — one aggregate Grok gate call for the whole skill
        # ------------------------------------------------------------------

        if gate_client and all_survivors and original_query:
            from agents.source_gate import pass2_gate
            approved_urls = await pass2_gate(gate_client, original_query, all_survivors)
            final_pairs = [
                (src, q) for src, q in all_survivors
                if src.get("url") in approved_urls
            ]
            if not final_pairs:
                final_pairs = all_survivors   # fallback: gate returned nothing useful
        else:
            final_pairs = all_survivors

        # ------------------------------------------------------------------
        # Step 3: Ingest approved sources into Qdrant
        # ------------------------------------------------------------------

        total_chunks  = 0
        total_sources = 0
        all_sources: list[dict] = []

        for src, q in final_pairs:
            text = src.get("content", "") or src.get("snippet", "") or src.get("abstract", "")
            if not text:
                continue
            base_cred    = src.get("credibility_base", 0.7)
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
            total_chunks  += len(chunks)
            total_sources += 1
            all_sources.append(src)

        # Register citations
        cit_reg = getattr(ctx, "citation_registry", None)
        if cit_reg is not None:
            for src in all_sources:
                cid = cit_reg.register(src, self.name, node.output_slot)
                src["citation_id"] = cid

        gate_info = (
            f", gate={len(all_survivors)}→{total_sources}"
            if (gate_client and original_query) else ""
        )
        _ = gate_info   # available for callers who want to log it

        return {
            "skill":          self.name,
            "queries_run":    len(queries),
            "sources_found":  total_sources,
            "chunks_stored":  total_chunks,
            "gate_survivors": len(all_survivors) if (gate_client and original_query) else None,
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
        """Map depth → max_results. Integer depth_override is used directly (strength-based)."""
        if isinstance(node.depth_override, int):
            return node.depth_override
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
