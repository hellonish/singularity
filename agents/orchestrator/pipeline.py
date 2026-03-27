"""
Phase 5 pipeline — research run (new execution order).

Phase B — Planning:    3 Managers propose structure → Lead finalises tree
Phase A — Retrieval:   tree-informed skill selection → targeted query fanout → Qdrant
Phase C — Writing:     Workers write sections bottom-up through the hierarchy
Phase D — Polish:      Programmatic fixes + LLM creative beautification

Retrieval now runs AFTER planning so every query is targeted at a real section.

Entry point: run_pipeline(query, strength, audience, output_language) → str (Markdown)
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from .config import (
    PLANNER_MODEL, MANAGER_MODEL, LEAD_MODEL,
    WORKER_ANALYSIS_MODEL, WORKER_WRITE_MODEL, POLISHER_MODEL,
)
from .strength import StrengthConfig
from models import ExecutionContext
from skills import SKILL_REGISTRY, TIER1_SKILLS

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
    logger: TraceLogger | None = None,
) -> ReportTree:
    """
    Run 3 Managers in parallel → Lead finalises.
    Managers receive the full list of available retrieval skills (retrieval runs
    AFTER planning, so skills are not yet filtered — we pass the full tier-1 set).
    Returns the authoritative ReportTree.
    """
    print(f"\n[Phase B] Planning — 3 Managers + Lead")

    # Roll section count once — immutable for this run
    target_n = strength.sample_section_count()
    lo, hi = strength.section_count_range
    print(f"  Section count rolled: {target_n}  (range {lo}–{hi})")

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
            logger=logger,
        )
        for m in managers
    ])

    for i, p in enumerate(proposals):
        print(f"  Manager {i+1}: {len(p.nodes)} nodes — {p.rationale[:60]}")

    print(f"  Lead model     : {LEAD_MODEL}")
    lead = ReportLeadAgent(client=_make_client(LEAD_MODEL))
    final_tree = await lead.finalise(
        proposals=list(proposals),
        query=query,
        section_count_range=(lo, hi),
        audience=audience,
        logger=logger,
    )

    print(f"  Lead finalised: {len(final_tree.nodes)} nodes, "
          f"depth={final_tree.max_depth}")
    return final_tree


# ---------------------------------------------------------------------------
# Phase C — Writing (Worker agents, bottom-up)
# ---------------------------------------------------------------------------

async def _phase_c(
    tree: ReportTree,
    run_id: str,
    strength: StrengthConfig,
    audience: str,
    query: str,
    vs: VectorStoreClient,
    logger: TraceLogger | None = None,
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

    Returns a merged source_map (citation_id → {title, url}) collected from
    all workers, used by the assembler to build the Reference List.
    """
    print(f"\n[Phase C] Writing — {len(tree.nodes)} sections, "
          f"{len(tree.leaves())} leaves")
    print(f"  Analysis model : {WORKER_ANALYSIS_MODEL}")
    print(f"  Write model    : {WORKER_WRITE_MODEL}")

    analysis_client = _make_client(WORKER_ANALYSIS_MODEL)
    write_client    = _make_client(WORKER_WRITE_MODEL)

    levels = tree.topological_levels()   # deepest → root (already reversed)

    for level_nodes in levels:
        depth = level_nodes[0].level
        print(f"  Writing depth={depth} ({len(level_nodes)} nodes) in parallel…")

        async def _write_node(node) -> None:
            k = strength.qdrant_k(node.level, tree.max_depth)
            chunks = vs.search(
                run_id=run_id,
                query_text=f"{node.title}: {node.description}",
                k=k,
            )
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
                logger=logger,
            )
            print(f"    [{node.node_id}] '{node.title[:40]}' "
                  f"→ {result.word_count} words, {len(result.citations_used)} citations")

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

    print("=" * 65)
    print("RESEARCH AGENT — PHASE 5 STRENGTH-BASED PIPELINE")
    print("=" * 65)
    print(f"Query    : {query}")
    print(f"Strength : {sc}")
    print(f"Audience : {audience}")
    print(f"Run ID   : {run_id}")

    logger: TraceLogger | None = None
    if trace:
        logger = TraceLogger(run_id=run_id, query=query, trace_root=trace_root)
        logger.write_overview({
            "strength":             strength,
            "audience":             audience,
            "output_language":      output_language,
            "manager_model":        MANAGER_MODEL,
            "lead_model":           LEAD_MODEL,
            "worker_analysis_model": WORKER_ANALYSIS_MODEL,
            "worker_write_model":   WORKER_WRITE_MODEL,
            "polisher_model":       POLISHER_MODEL,
        })
        print(f"  Trace    : enabled → {trace_root}/{run_id}/")

    ctx = ExecutionContext(language=output_language, depth="strength")

    vs = VectorStoreClient()

    # ── Phase B — Planning (first: defines structure before retrieval) ─
    tree = await _phase_b(
        query=query,
        strength=sc,
        available_skills=list(TIER1_SKILLS),   # full tier-1 set — retrieval picks later
        audience=audience,
        logger=logger,
    )

    # ── Topic cache check (triggers lazy Qdrant init + server probe) ──
    cached_run_id = vs.find_cached_run(query)   # returns None if in-memory or no hit

    if cached_run_id:
        print(f"\n[Cache HIT] Reusing collection from run {cached_run_id}")
        active_run_id = cached_run_id
    else:
        # ── Phase A — Retrieval (tree-informed: queries target real sections) ─
        collection_name = vs.create_collection(run_id)
        active_run_id = run_id

        retriever = Retriever(_make_client(PLANNER_MODEL), vs)
        await retriever.run(query, sc, run_id, collection_name, ctx, tree=tree, logger=logger)

    # ── Phase C ───────────────────────────────────────────────────────
    source_map = await _phase_c(
        tree=tree,
        run_id=active_run_id,
        strength=sc,
        audience=audience,
        query=query,
        vs=vs,
        logger=logger,
    )

    # ── Assemble report ───────────────────────────────────────────────
    cred_avg = None
    if ctx.credibility_scores:
        cred_avg = sum(ctx.credibility_scores.values()) / len(ctx.credibility_scores)

    report_md = _format_report(tree, query, cred_avg, source_map=source_map)

    total_words = sum(n.word_count for n in tree.nodes)

    # ── Phase D — Polish ──────────────────────────────────────────────
    print(f"\n[Phase D] Polish — programmatic fixes + creative formatting")
    report_md = await _phase_d(report_md, query, audience, logger=logger)

    print(f"\n{'=' * 65}")
    print("RESEARCH COMPLETE")
    print(f"  Sections written : {len(tree.nodes)}")
    print(f"  Total words      : {total_words:,}")
    print(f"  Report length    : {len(report_md):,} chars")
    if logger is not None:
        print(f"  Trace saved      : {trace_root}/{run_id}/")

    return report_md


async def _phase_d(
    report_md: str,
    query: str,
    audience: str,
    logger: TraceLogger | None = None,
) -> str:
    """Phase D — Polish the assembled report for visual excellence."""
    from agents.polish import PolishAgent
    polisher = PolishAgent(POLISHER_MODEL, logger=logger)
    polished = await polisher.polish(report_md, query, audience)
    print(f"  Polish complete  : {len(polished):,} chars")
    return polished
