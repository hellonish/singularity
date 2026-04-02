"""
Retriever agent — Phase A of the research pipeline.

Three-step planner (Issue 6):
  Step 1 — Skill selection with explicit reasoning; web_search always injected.
  Step 2 — Query generation per (skill × section-cluster); returns {query, for_sections}.
  Step 3 — Post-processing sanitizer strips ALL internal annotations before
            any query reaches a live API.  Runs unconditionally.

Issue 2 Fix 4: section-normalised query budget ensures each leaf section gets
at least one dedicated query across the skill set.
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from models import ExecutionContext, PlanNode
from skills import SKILL_REGISTRY, TIER1_SKILLS
from utils.json_parser import extract_object

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text(encoding="utf-8")

QUERY_MAX_CHARS         = 150   # hard cap on query string length
JACCARD_DEDUP_THRESHOLD = 0.75  # queries with Jaccard similarity above this are duplicates

if TYPE_CHECKING:
    from trace import TraceLogger


# ---------------------------------------------------------------------------
# Query sanitizer — runs on EVERY query string before it touches any API
# ---------------------------------------------------------------------------

_ANNOTATION_PATTERNS: list[re.Pattern] = [
    re.compile(r'\s*\(for\s+[Ss]ections?\s+[^)]+\)',     re.IGNORECASE),
    re.compile(r'\s*\([Ss]ection\s*\d+[^)]*\)',           re.IGNORECASE),
    re.compile(r'\s*\[node[_\s]?id[^\]]+\]',              re.IGNORECASE),
    re.compile(r'\s*\(n\d+[^)]*\)',                        re.IGNORECASE),
    re.compile(r'\s*-\s*for\s+section\s+\d+.*$',          re.IGNORECASE),
    re.compile(r'\s*\(targets?\s*:?\s*[^)]+\)',            re.IGNORECASE),
    re.compile(r'\s*\[targets?\s*:?\s*[^\]]+\]',          re.IGNORECASE),
    re.compile(r'\s*\(section\s+\w+\s*:.*?\)',             re.IGNORECASE),
]


def sanitize_query(q: str) -> str:
    """
    Strip all internal annotations from a query string and enforce length cap.
    This is the single source of truth for query cleaning — call before every
    API request, regardless of how the query was generated.
    """
    for pattern in _ANNOTATION_PATTERNS:
        q = pattern.sub('', q)
    q = q.strip(' .,;:-')
    # Hard cap at QUERY_MAX_CHARS, breaking at a word boundary
    if len(q) > QUERY_MAX_CHARS:
        q = q[:QUERY_MAX_CHARS].rsplit(' ', 1)[0]
    return q.strip()


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class Retriever:
    """
    Encapsulates Phase A: skill selection → query generation → sanitize → fanout → Qdrant.

    Usage:
        retriever = Retriever(llm_client, vector_store_client)
        active_skills = await retriever.run(
            query, strength, run_id, collection_name, ctx, tree=tree, trace_logger=tl
        )
    """

    def __init__(self, client, vs):
        self.client = client
        self.vs = vs

    async def run(
        self,
        query: str,
        strength,           # StrengthConfig
        run_id: str,
        collection_name: str,
        ctx: ExecutionContext,
        tree=None,          # ReportTree | None
        trace_logger: "TraceLogger | None" = None,
        domain_key: str | None = None,
        domain_label: str | None = None,
        domain_confidence: str | None = None,
        gate_client=None,   # GrokClient | None — enables 2-pass source gate
    ) -> list[str]:
        """
        Run retrieval phase. Returns list of active skill names.

        Three-step planner:
          Step 1: Skill selection — LLM picks best skills + reasoning.
          Step 2: Query generation — LLM generates clean queries per skill.
          Step 3: Sanitizer — strips annotations, enforces length cap.
        web_search is always injected regardless of LLM choices.

        When ``domain_key`` is set (from a small classifier call), it is passed into
        the user prompt so skill selection aligns with the research domain.

        ``trace_logger`` is only for disk trace artifacts; standard Phase A lines
        go to the module logger so runs work with tracing off.
        """
        from skills.tier1_retrieval.base import BaseRetrievalSkill
        retrieval_registry: dict[str, BaseRetrievalSkill] = {
            k: v for k, v in SKILL_REGISTRY.items()
            if k in TIER1_SKILLS and isinstance(v, BaseRetrievalSkill)
        }

        # Build section context for targeted query generation
        leaf_count = len([n for n in tree.nodes if not tree.children_of(n.node_id)]) if tree else 0
        section_context = ""
        if tree is not None:
            topics = [
                f"  - [{n.node_id}] {n.title}: {n.description[:80]}"
                for n in tree.nodes
            ]
            section_context = (
                f"report_sections ({len(tree.nodes)} planned, {leaf_count} leaf sections):\n"
                + "\n".join(topics)
                + "\n\n"
            )

        # Effective queries per skill (section-normalised per Issue 2 Fix 4)
        effective_qps = strength.effective_queries_per_skill(leaf_count) if leaf_count else strength.queries_per_skill

        # ── Step 1 + Step 2: Single structured LLM call ──────────────────
        system_prompt = _SYSTEM_PROMPT

        domain_block = ""
        if domain_key:
            domain_block = (
                f"classified_domain_key: {domain_key}\n"
                f"classified_domain_label: {domain_label or domain_key}\n"
                f"classified_domain_confidence: {domain_confidence or 'unknown'}\n"
                "Use this as the primary signal for which retrieval skills fit the "
                "query; override only if the question clearly contradicts it.\n\n"
            )

        user_prompt = (
            f"mode: retrieval_plan\n"
            f"research_query: {query}\n"
            f"{domain_block}"
            f"{section_context}"
            f"available_skills: {', '.join(retrieval_registry.keys())}\n"
            f"select_n_skills: {strength.retrieval_skill_count - 1}  "
            f"(web_search is always added automatically — do not include it)\n"
            f"queries_per_skill: {effective_qps}\n\n"
            f"Return this exact JSON structure:\n"
            f"{{\n"
            f'  "skill_selection": {{\n'
            f'    "selected": ["skill_name", ...],\n'
            f'    "reasoning": {{"skill_name": "why this skill fits this query"}}\n'
            f"  }},\n"
            f'  "skill_queries": {{\n'
            f'    "skill_name": [\n'
            f'      {{"query": "clean web search string", "for_sections": ["n1", "n3"]}},\n'
            f"      ...\n"
            f"    ]\n"
            f"  }}\n"
            f"}}\n\n"
            f"Generate exactly {effective_qps} queries per skill. "
            f"Each query must target one or more specific sections from the list above. "
            f"Queries within a skill must be semantically diverse — no paraphrases."
        )

        raw = self.client.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
        )

        skill_queries = self._parse_and_sanitize(
            raw, strength, effective_qps, query, retrieval_registry
        )

        # ── Step 3: Always inject web_search ─────────────────────────────
        if "web_search" not in skill_queries:
            # Generate targeted web queries from the first few section titles
            web_fallback_queries = [query]
            if tree:
                leaf_titles = [n.title for n in tree.leaves()[:effective_qps - 1]]
                web_fallback_queries += [f"{query} {t}" for t in leaf_titles]
            skill_queries["web_search"] = web_fallback_queries[:effective_qps]

        # ── Step 4 (strength ≥ 7): adversarial query in web_search ─────────
        if strength.value >= 7 and "web_search" in skill_queries:
            adv_q = sanitize_query(_make_adversarial_query(query))
            if adv_q:
                skill_queries["web_search"].append(adv_q)

        active_skills = list(skill_queries.keys())
        section_hint = f" (targeting {len(tree.nodes)} sections)" if tree else ""
        logger.info(
            "\n[Phase A] Retrieval%s — %d skills × %d queries",
            section_hint, len(active_skills), effective_qps,
        )
        logger.info("  Active skills: %s", active_skills)

        if trace_logger is not None:
            trace_logger.log_retriever_plan(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                raw_response=raw,
                skill_queries={k: v if isinstance(v[0], str) else [q["query"] for q in v]
                               for k, v in skill_queries.items()},
            )

        async def _run_skill(skill_name: str, queries: list[str]) -> None:
            skill = retrieval_registry.get(skill_name)
            if skill is None:
                logger.warning("  skill '%s' not in retrieval registry — skipping", skill_name)
                return
            node = PlanNode(
                node_id=f"retrieval_{skill_name}",
                description=query,
                skill=skill_name,
                depends_on=[],
                acceptance=[],
                parallelizable=True,
                output_slot=f"retrieval_{skill_name}",
                depth_override=strength.min_results_per_query,
            )
            summary = await skill.run_fanout(
                queries=queries,
                run_id=run_id,
                collection_name=collection_name,
                node=node,
                ctx=ctx,
                vs=self.vs,
                original_query=query,
                gate_client=gate_client,
            )
            gate_str = (
                f", gate {summary['gate_survivors']}→{summary['sources_found']}"
                if summary.get("gate_survivors") is not None else ""
            )
            logger.info(
                "  [%s] %d sources → %d chunks%s",
                skill_name, summary["sources_found"], summary["chunks_stored"], gate_str,
            )
            if trace_logger is not None:
                trace_logger.log_skill_result(
                    skill_name=skill_name,
                    queries=queries,
                    sources_found=summary.get("sources_found", 0),
                    chunks_stored=summary.get("chunks_stored", 0),
                )

        await asyncio.gather(*[
            _run_skill(name, queries) for name, queries in skill_queries.items()
        ])
        self.vs.register_run_in_cache(run_id, query)
        return active_skills

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_and_sanitize(
        self,
        raw: str,
        strength,
        queries_per_skill: int,
        fallback_query: str,
        retrieval_registry: dict,
    ) -> dict[str, list[str]]:
        """
        Parse the LLM response, extract clean query strings, and run the
        mandatory sanitizer on every query before returning.

        Accepts two output formats:
          1. New format: skill_queries values are [{query: str, for_sections: [...]}]
          2. Legacy format: skill_queries values are [str, str, ...]
        """
        obj: dict = extract_object(raw) or {}

        # Support both the new nested structure and legacy flat structure
        sq_raw = obj.get("skill_queries", obj)
        if not isinstance(sq_raw, dict):
            sq_raw = {}

        result: dict[str, list[str]] = {}
        q = queries_per_skill

        for skill, entries in list(sq_raw.items())[:strength.retrieval_skill_count]:
            if skill not in retrieval_registry:
                continue
            if not isinstance(entries, list) or not entries:
                entries = [fallback_query]

            # Normalise: extract .query if dict, else use string directly
            queries: list[str] = []
            for entry in entries:
                if isinstance(entry, dict):
                    raw_q = entry.get("query", fallback_query)
                else:
                    raw_q = str(entry)
                cleaned = sanitize_query(raw_q)
                if cleaned:
                    queries.append(cleaned)

            # Ensure diversity: deduplicate near-identical queries
            queries = _deduplicate_queries(queries)

            # Pad or trim to exact count
            while len(queries) < q:
                queries.append(sanitize_query(fallback_query))
            result[skill] = queries[:q]

        if not result:
            # Full fallback
            fallback_skills = list(retrieval_registry.keys())[:strength.retrieval_skill_count]
            for s in fallback_skills:
                result[s] = [sanitize_query(fallback_query)] * q

        return result


def _make_adversarial_query(query: str) -> str:
    """
    Devil's advocate search query — targets criticism, risks, limitations,
    or failure cases for the main topic.  Injected into web_search at strength ≥ 7.
    """
    skip = {"what", "how", "why", "is", "are", "the", "a", "an",
            "of", "in", "and", "to", "for", "does", "do", "can", "will"}
    words = [w for w in query.split() if w.lower() not in skip][:7]
    topic = " ".join(words)
    return f"criticism limitations failure risks problems {topic}"


def _deduplicate_queries(queries: list[str]) -> list[str]:
    """
    Remove queries that are too similar to an already-accepted query.
    Uses simple word-overlap (Jaccard) as a cheap diversity proxy.
    Threshold: if Jaccard > 0.75, treat as duplicate.
    """
    accepted: list[str] = []
    accepted_sets: list[set[str]] = []
    for q in queries:
        words = set(q.lower().split())
        if not words:
            continue
        is_dup = any(
            len(words & acc) / len(words | acc) > JACCARD_DEDUP_THRESHOLD
            for acc in accepted_sets
        )
        if not is_dup:
            accepted.append(q)
            accepted_sets.append(words)
    return accepted if accepted else queries  # never return empty
