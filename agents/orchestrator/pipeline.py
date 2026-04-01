"""
run_pipeline — Phase 5 research pipeline (current primary production path).

WHEN TO USE THIS vs run_orchestrator
--------------------------------------
Use ``run_pipeline`` (this module) for all full research reports.  It is the
CURRENT production path.

Use ``run_orchestrator`` (agents/orchestrator/runner.py) for legacy DAG-style
skill execution or the replan-loop flow.  See runner.py for the full comparison.

Phase sequence
--------------
Phase B — Planning:    3 Managers propose tree structure → Lead finalises
Phase A — Retrieval:   tree-informed skill selection → targeted query fanout → Qdrant
Phase C — Writing:     Workers write sections bottom-up through the report tree
Phase D — Polish:      Programmatic fixes + LLM creative beautification

Retrieval runs AFTER planning so every query targets a real planned section.

Entry point: run_pipeline(query, strength, audience, output_language) → str (Markdown)
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from functools import partial
from pathlib import Path

logger = logging.getLogger(__name__)

from .config import (
    PLANNER_MODEL, MANAGER_MODEL, LEAD_MODEL,
    WORKER_ANALYSIS_MODEL, WORKER_WRITE_MODEL, POLISHER_MODEL,
    DOMAIN_CLASSIFIER_MODEL, MAX_TOKENS_DOMAIN_CLASSIFIER, REGISTRY_PATH,
    SOURCE_GATE_MODEL,
)
from .strength import StrengthConfig
from models import ExecutionContext, PlanNode
from skills import SKILL_REGISTRY, TIER1_SKILLS, SKILL_DOCS

from agents.planner import DomainRegistry
from agents.report_manager import ReportManagerAgent, ReportTree
from agents.report_lead import ReportLeadAgent
from agents.report_worker import ReportWorkerAgent
from agents.retriever import Retriever
from vector_store.client import VectorStoreClient
from trace import TraceLogger

import sys
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from llm.grok import GrokClient  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(model: str) -> GrokClient:
    return GrokClient(model_name=model)


# Domains that should never appear in a published reference list.
# Typically translation proxies, redirectors, or content farms.
_JUNK_DOMAINS = frozenset({
    "translate.yandex.com",
    "translate.google.com",
    "translate.goo.ne.jp",
    "web.archive.org",
    "webcache.googleusercontent.com",
    "cache.google.com",
    "amp.reddit.com",
    "l.facebook.com",
    "t.co",
    "bit.ly",
    "tinyurl.com",
})


def _is_junk_url(url: str) -> bool:
    """Returns True if the URL belongs to a known junk/redirect domain."""
    if not url:
        return False
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lstrip("www.").lower()
        return domain in _JUNK_DOMAINS or any(
            domain.endswith("." + d) for d in _JUNK_DOMAINS
        )
    except Exception:
        return False


def _format_report(
    tree: ReportTree,
    query: str,
    cred_avg: float | None,
    source_map: dict[str, dict] | None = None,
) -> str:
    """
    Assemble the final Markdown document from the written tree.

    Appends a single Reference List built from `source_map`
    (citation_id → {title, url, source_type, date}) collected by the workers.
    Entries are ordered by first appearance in the tree (reading order) and
    junk URLs are filtered out.  The legacy CitationRegistry bib_md block is
    intentionally dropped — it duplicated entries with worse metadata.
    """
    parts = [
        f"# Research Report\n\n**Query:** {query}\n\n---\n",
    ]

    # Track citation first-appearance order via reading-order tree walk
    appearance_order: list[str] = []
    seen_order: set[str] = set()

    def _walk(node_id: str, depth: int) -> None:
        node = tree.by_id(node_id)
        if node is None:
            return
        heading = "#" * min(depth + 1, 6)
        parts.append(f"{heading} {node.title}\n\n{node.content}\n")
        # Record citation order from this node's source_map keys
        for cite_id in (node.source_map or {}).keys():
            if cite_id not in seen_order:
                seen_order.add(cite_id)
                appearance_order.append(cite_id)
        for child in tree.children_of(node_id):
            _walk(child.node_id, depth + 1)

    _walk(tree.root.node_id, 1)

    if source_map:
        # Any keys not reached by reading-order walk (e.g. parent-only sources)
        for cite_id in source_map:
            if cite_id not in seen_order:
                appearance_order.append(cite_id)

        ref_lines: list[str] = []
        for cite_id in appearance_order:
            info = source_map.get(cite_id)
            if not info:
                continue
            title       = (info.get("title") or "").strip()
            url         = (info.get("url") or "").strip()
            source_type = (info.get("source_type") or "").strip()
            date        = (info.get("date") or "").strip()

            if _is_junk_url(url):
                continue

            # Build the entry: [CiteKey] Title (type · date) url
            label = f"**{cite_id}**"
            if title and url:
                body = f"[{title}]({url})"
            elif title:
                body = title
            elif url:
                body = f"[{url}]({url})"
            else:
                continue   # Nothing useful — skip entirely

            meta_parts = []
            if source_type:
                meta_parts.append(source_type)
            if date:
                meta_parts.append(date[:7])   # YYYY-MM at most
            meta = f" · *{' · '.join(meta_parts)}*" if meta_parts else ""

            ref_lines.append(f"- {label} {body}{meta}")

        if ref_lines:
            parts.append("\n---\n\n## Reference List\n\n" + "\n".join(ref_lines))

    if cred_avg is not None:
        parts.append(f"\n\n---\n\n*Mean source credibility: {cred_avg:.2f} / 1.00*\n")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Phase B — Planning (Manager + Lead)
# ---------------------------------------------------------------------------

async def _phase_b(
    query: str,
    strength: StrengthConfig,
    available_skills: list[str],
    audience: str,
    trace_logger: TraceLogger | None = None,
) -> ReportTree:
    """
    Run 3 Managers in parallel → Lead finalises.
    Managers receive the full list of available retrieval skills (retrieval runs
    AFTER planning, so skills are not yet filtered — we pass the full tier-1 set)
    plus their full skill contracts (When to Use, Output Contract, Constraints)
    sourced from each skill's skill.md so managers can assign skills to sections
    with full awareness of what each skill produces.
    Returns the authoritative ReportTree.
    """
    logger.info("\n[Phase B] Planning — 3 Managers + Lead")

    # Roll section count once — immutable for this run
    target_n = strength.sample_section_count()
    lo, hi = strength.section_count_range
    logger.info("  Section count rolled: %d  (range %d–%d)", target_n, lo, hi)

    skill_context = SKILL_DOCS.planner_context(available_skills)

    manager_client = _make_client(MANAGER_MODEL)
    managers = [
        ReportManagerAgent(manager_id=i + 1, client=manager_client)
        for i in range(3)
    ]

    proposals = await asyncio.gather(*[
        m.propose(
            query=query,
            target_n=target_n,
            available_skills=available_skills,
            audience=audience,
            skill_context=skill_context,
            logger=trace_logger,
        )
        for m in managers
    ])

    for i, p in enumerate(proposals):
        logger.info("  Manager %d: %d nodes — %s", i + 1, len(p.nodes), p.rationale[:60])

    logger.info("  Lead model     : %s", LEAD_MODEL)
    lead = ReportLeadAgent(client=_make_client(LEAD_MODEL))
    final_tree = await lead.finalise(
        proposals=list(proposals),
        query=query,
        section_count_range=(lo, hi),
        audience=audience,
        logger=trace_logger,
    )

    logger.info("  Lead finalised: %d nodes, depth=%d", len(final_tree.nodes), final_tree.max_depth)
    return final_tree


# ---------------------------------------------------------------------------
# Phase C — Writing (Worker agents, bottom-up)
# ---------------------------------------------------------------------------

async def _layer1_coverage_audit(
    tree: ReportTree,
    run_id: str,
    collection_name: str,
    strength: StrengthConfig,
    vs: VectorStoreClient,
    query: str,
    ctx,
    gate_client=None,
) -> None:
    """
    Issue 1 Layer 1: Post-Phase-A coverage audit.

    For each leaf section with fewer than strength.min_chunks_per_leaf evidence
    chunks, run a targeted web search follow-up to fill the gap before writing.
    """
    from agents.retriever.retriever import sanitize_query
    from skills import SKILL_REGISTRY

    leaves = tree.leaves()
    min_chunks = strength.min_chunks_per_leaf
    starved: list = []

    for leaf in leaves:
        section_q = f"{leaf.title}: {leaf.description}"
        count = vs.count_chunks(run_id=run_id, query_text=section_q, k=min_chunks + 10)
        if count < min_chunks:
            starved.append(leaf)

    if not starved:
        logger.info(
            "\n[Layer 1 Audit] All %d leaf sections meet coverage threshold (min=%d)",
            len(leaves), min_chunks,
        )
        return

    logger.info(
        "\n[Layer 1 Audit] %d/%d sections starved (< %d chunks) — targeted re-retrieval",
        len(starved), len(leaves), min_chunks,
    )

    web_skill = SKILL_REGISTRY.get("web_search")
    if web_skill is None:
        logger.warning("[Layer 1] web_search skill not found — skipping re-retrieval")
        return

    async def _refetch(node) -> None:
        q = sanitize_query(f"{query} {node.title} {node.description[:60]}")
        pnode = PlanNode(
            node_id=f"layer1_{node.node_id}",
            description=q,
            skill="web_search",
            depends_on=[],
            acceptance=[],
            parallelizable=True,
            output_slot=f"layer1_{node.node_id}",
            depth_override=strength.min_results_per_query,
        )
        summary = await web_skill.run_fanout(
            queries=[q],
            run_id=run_id,
            collection_name=collection_name,
            node=pnode,
            ctx=ctx,
            vs=vs,
            original_query=query,
            gate_client=gate_client,
        )
        logger.info(
            "    [Layer 1] %s '%s' → +%d chunks",
            node.node_id, node.title[:35], summary["chunks_stored"],
        )

    await asyncio.gather(*[_refetch(n) for n in starved])


async def _phase_c(
    tree: ReportTree,
    run_id: str,
    collection_name: str,
    strength: StrengthConfig,
    audience: str,
    query: str,
    vs: VectorStoreClient,
    ctx,
    trace_logger: TraceLogger | None = None,
    gate_client=None,
) -> dict[str, dict]:
    """
    Spawn one ReportWorkerAgent per node.
    Execute bottom-up: deepest level first, root last.
    Workers at the same depth level run in parallel.

    Two separate LLM clients are used per worker:
      analysis_client (WORKER_ANALYSIS_MODEL) — Call 1: structured JSON analysis,
        high-volume, cost-sensitive; mini model is sufficient.
      write_client    (WORKER_WRITE_MODEL)     — Call 2: the actual published prose;
        best available non-reasoning model for maximum quality.

    Issue 3 (Phase C+): leaf workers receive strength/vs/collection_name so they
    can run the evidence augmentation loop between Call 1 and Call 2.

    Issue 4: parent node Qdrant queries include child titles for richer context.

    Issue 5: time-sensitive nodes (requires_fresh=True) get a JIT web search
    immediately before their worker runs.

    Returns a merged source_map (citation_id → {title, url}) collected from
    all workers, used by the assembler to build the Reference List.
    """
    from agents.retriever.retriever import sanitize_query
    from skills import SKILL_REGISTRY

    logger.info("\n[Phase C] Writing — %d sections, %d leaves", len(tree.nodes), len(tree.leaves()))
    logger.info("  Analysis model : %s", WORKER_ANALYSIS_MODEL)
    logger.info("  Write model    : %s", WORKER_WRITE_MODEL)
    aug_enabled = strength.max_augmentation_iters > 0
    logger.info(
        "  Phase C+ augmentation: %s (max_iters=%d, max_web_esc=%d)",
        "enabled" if aug_enabled else "disabled",
        strength.max_augmentation_iters,
        strength.max_web_escalations,
    )

    analysis_client = _make_client(WORKER_ANALYSIS_MODEL)
    write_client    = _make_client(WORKER_WRITE_MODEL)
    web_skill = SKILL_REGISTRY.get("web_search")

    levels = tree.topological_levels()   # deepest → root (already reversed)

    for level_nodes in levels:
        depth = level_nodes[0].level
        is_leaf_level = (depth == tree.max_depth)
        logger.info("  Writing depth=%d (%d nodes) in parallel…", depth, len(level_nodes))

        async def _write_node(node) -> None:
            k = strength.qdrant_k(node.level, tree.max_depth)
            is_leaf = len(tree.children_of(node.node_id)) == 0

            # Issue 5: JIT fresh search for time-sensitive sections
            if getattr(node, "requires_fresh", False) and web_skill is not None:
                fresh_q = sanitize_query(f"{query} {node.title} {node.description[:60]}")
                fresh_node = PlanNode(
                    node_id=f"jit_{node.node_id}",
                    description=fresh_q,
                    skill="web_search",
                    depends_on=[],
                    acceptance=[],
                    parallelizable=True,
                    output_slot=f"jit_{node.node_id}",
                    depth_override=strength.min_results_per_query,
                )
                await web_skill.run_fanout(
                    queries=[fresh_q],
                    run_id=run_id,
                    collection_name=collection_name,
                    node=fresh_node,
                    ctx=ctx,
                    vs=vs,
                    original_query=query,
                    gate_client=gate_client,
                )

            # Issue 4: include child titles in parent node query for richer context
            children = tree.children_of(node.node_id)
            if children:
                child_titles = " ".join(c.title for c in children[:4])
                query_text = f"{node.title}: {node.description} {child_titles}"
            else:
                query_text = f"{node.title}: {node.description}"

            chunks = vs.search(run_id=run_id, query_text=query_text, k=k)

            worker = ReportWorkerAgent(
                node=node,
                tree=tree,
                run_id=run_id,
                analysis_client=analysis_client,
                write_client=write_client,
            )
            result = await worker.run(
                qdrant_chunks=chunks,
                audience=audience,
                research_query=query,
                logger=trace_logger,
                # Issue 3: Phase C+ parameters (leaf nodes only)
                strength=strength if is_leaf else None,
                collection_name=collection_name if is_leaf else None,
                vs=vs if is_leaf else None,
                ctx=ctx,
            )

            aug_info = ""
            if is_leaf and result.augmentation_iters > 0:
                aug_info = (f", aug_iters={result.augmentation_iters}"
                            f", faith={result.faithfulness_score:.2f}"
                            if result.faithfulness_score is not None
                            else f", aug_iters={result.augmentation_iters}")
            logger.info(
                "    [%s] '%s' → %d words, %d citations%s",
                node.node_id, node.title[:40],
                result.word_count, len(result.citations_used), aug_info,
            )

        await asyncio.gather(*[_write_node(n) for n in level_nodes])

    # Aggregate source maps from all nodes (written in-place by workers)
    merged: dict[str, dict] = {}
    for node in tree.nodes:
        merged.update(node.source_map)
    return merged


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_pipeline(
    query: str,
    strength: int = 5,
    audience: str = "practitioner",
    output_language: str = "en",
    trace: bool = False,
    trace_root: str = "traces",
) -> str:
    """
    Full Phase 5 pipeline. Returns the final Markdown report as a string.

    Args:
        query:           Research question.
        strength:        1–10 run strength (controls depth, section count, retrieval).
        audience:        Target reader type (practitioner / expert / layperson …).
        output_language: ISO 639-1 language code for the report.
        trace:           When True, write a structured trace directory to `trace_root`
                         containing every LLM prompt, raw response, and parsed output
                         for all phases (B planning, A retrieval, C writing, D polish).
        trace_root:      Directory under which per-run trace folders are created.
                         Each run gets its own sub-folder named by run_id.
    """
    sc = StrengthConfig(value=strength)
    run_id = uuid.uuid4().hex[:12]

    logger.info("=" * 65)
    logger.info("RESEARCH AGENT — PHASE 5 STRENGTH-BASED PIPELINE")
    logger.info("=" * 65)
    logger.info("Query    : %s", query)
    logger.info("Strength : %s", sc)
    logger.info("Audience : %s", audience)
    logger.info("Run ID   : %s", run_id)

    trace_logger: TraceLogger | None = None
    if trace:
        trace_logger = TraceLogger(run_id=run_id, query=query, trace_root=trace_root)
        trace_logger.write_overview({
            "strength":             strength,
            "audience":             audience,
            "output_language":      output_language,
            "manager_model":        MANAGER_MODEL,
            "lead_model":           LEAD_MODEL,
            "worker_analysis_model": WORKER_ANALYSIS_MODEL,
            "worker_write_model":   WORKER_WRITE_MODEL,
            "polisher_model":       POLISHER_MODEL,
        })
        logger.info("  Trace    : enabled → %s/%s/", trace_root, run_id)

    ctx = ExecutionContext(language=output_language, depth="strength")

    vs = VectorStoreClient()
    gate_client = _make_client(SOURCE_GATE_MODEL)

    domain_registry = DomainRegistry(REGISTRY_PATH)
    domain_client = _make_client(DOMAIN_CLASSIFIER_MODEL)
    classified_domain, domain_conf = await asyncio.to_thread(
        partial(
            domain_registry.detect_domain_llm,
            query,
            domain_client,
            max_tokens=MAX_TOKENS_DOMAIN_CLASSIFIER,
        )
    )
    dinfo = domain_registry.get_domain(classified_domain)
    domain_label = dinfo.get("label", classified_domain)
    logger.info("  Domain     : %s — %s (%s)", classified_domain, domain_label, domain_conf)

    # ── Phase B — Planning (first: defines structure before retrieval) ─
    tree = await _phase_b(
        query=query,
        strength=sc,
        available_skills=list(TIER1_SKILLS),   # full tier-1 set — retrieval picks later
        audience=audience,
        trace_logger=trace_logger,
    )

    # ── Topic cache check (triggers lazy Qdrant init + server probe) ──
    cached_run_id = vs.find_cached_run(query)   # returns None if in-memory or no hit

    if cached_run_id:
        logger.info("\n[Cache HIT] Reusing collection from run %s", cached_run_id)
        active_run_id = cached_run_id
        active_collection = f"run_{cached_run_id}"
    else:
        # ── Phase A — Retrieval (tree-informed: queries target real sections) ─
        active_collection = vs.create_collection(run_id)
        active_run_id = run_id

        retriever = Retriever(_make_client(PLANNER_MODEL), vs)
        await retriever.run(
            query,
            sc,
            run_id,
            active_collection,
            ctx,
            tree=tree,
            logger=trace_logger,
            domain_key=classified_domain,
            domain_label=domain_label,
            domain_confidence=domain_conf,
            gate_client=gate_client,
        )

        # ── Issue 1 Layer 1: Coverage audit — re-fetch starved sections ──
        await _layer1_coverage_audit(
            tree=tree,
            run_id=active_run_id,
            collection_name=active_collection,
            strength=sc,
            vs=vs,
            query=query,
            ctx=ctx,
            gate_client=gate_client,
        )

    # ── Phase C ───────────────────────────────────────────────────────
    source_map = await _phase_c(
        tree=tree,
        run_id=active_run_id,
        collection_name=active_collection,
        strength=sc,
        audience=audience,
        query=query,
        vs=vs,
        ctx=ctx,
        trace_logger=trace_logger,
        gate_client=gate_client,
    )

    # ── Assemble report ───────────────────────────────────────────────
    cred_avg = None
    if ctx.credibility_scores:
        cred_avg = sum(ctx.credibility_scores.values()) / len(ctx.credibility_scores)

    report_md = _format_report(tree, query, cred_avg, source_map=source_map)

    total_words = sum(n.word_count for n in tree.nodes)

    # ── Phase D — Polish ──────────────────────────────────────────────
    logger.info("\n[Phase D] Polish — programmatic fixes + creative formatting")
    report_md = await _phase_d(report_md, query, audience, trace_logger=trace_logger)

    logger.info("\n%s", "=" * 65)
    logger.info("RESEARCH COMPLETE")
    logger.info("  Sections written : %d", len(tree.nodes))
    logger.info("  Total words      : %s", f"{total_words:,}")
    logger.info("  Report length    : %s chars", f"{len(report_md):,}")
    if trace_logger is not None:
        logger.info("  Trace saved      : %s/%s/", trace_root, run_id)

    # Enforce TTL on stale run collections so Qdrant does not grow unbounded.
    try:
        deleted = vs.cleanup_expired_collections()
        if deleted:
            logger.debug("[VectorStore] Expired collections removed: %s", deleted)
    except Exception as exc:
        logger.warning("[VectorStore] cleanup_expired_collections failed: %s", exc)

    return report_md


async def _phase_d(
    report_md: str,
    query: str,
    audience: str,
    trace_logger: TraceLogger | None = None,
) -> str:
    """Phase D — Polish the assembled report for visual excellence."""
    from agents.polish import PolishAgent
    polisher = PolishAgent(POLISHER_MODEL, logger=trace_logger)
    polished = await polisher.polish(report_md, query, audience)
    logger.info("  Polish complete  : %s chars", f"{len(polished):,}")
    return polished
