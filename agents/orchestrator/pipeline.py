"""
Phase 5 pipeline — 3-phase product research run.

Phase A — Retrieval:   select skills → adaptive query fanout → ingest to Qdrant
Phase B — Planning:    3 Managers propose structure → Lead finalises tree
Phase C — Writing:     Workers write sections bottom-up through the hierarchy

Entry point: run_pipeline(query, strength, audience, output_language) → str (Markdown)
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from .config import (
    PLANNER_MODEL, MANAGER_MODEL, LEAD_MODEL, WORKER_MODEL,
)
from .strength import StrengthConfig
from models import ExecutionContext
from skills import SKILL_REGISTRY

from agents.report_manager import ReportManagerAgent, ReportTree
from agents.report_lead import ReportLeadAgent
from agents.report_worker import ReportWorkerAgent
from agents.retriever import Retriever
from vector_store.client import VectorStoreClient

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


def _format_report(tree: ReportTree, query: str, bib_md: str, cred_avg: float | None) -> str:
    """Assemble the final Markdown document from the written tree."""
    parts = [
        f"# Research Report\n\n**Query:** {query}\n\n---\n",
    ]

    def _walk(node_id: str, depth: int) -> None:
        node = tree.by_id(node_id)
        if node is None:
            return
        heading = "#" * min(depth + 1, 6)
        parts.append(f"{heading} {node.title}\n\n{node.content}\n")
        for child in tree.children_of(node_id):
            _walk(child.node_id, depth + 1)

    _walk(tree.root.node_id, 1)

    if bib_md.strip():
        parts.append(f"\n---\n\n## References\n\n{bib_md}")
    if cred_avg is not None:
        parts.append(f"\n\n---\n\n*Mean source credibility: {cred_avg:.2f} / 1.00*\n")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Phase B — Planning (Manager + Lead)
# ---------------------------------------------------------------------------

async def _phase_b(
    query: str,
    strength: StrengthConfig,
    active_skills: list[str],
    audience: str,
) -> ReportTree:
    """
    Run 3 Managers in parallel → Lead finalises.
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
            active_skills=active_skills,
            audience=audience,
        )
        for m in managers
    ])

    for i, p in enumerate(proposals):
        print(f"  Manager {i+1}: {len(p.nodes)} nodes — {p.rationale[:60]}")

    lead = ReportLeadAgent(client=_make_client(LEAD_MODEL))
    final_tree = await lead.finalise(
        proposals=list(proposals),
        query=query,
        section_count_range=(lo, hi),
        audience=audience,
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
) -> None:
    """
    Spawn one ReportWorkerAgent per node.
    Execute bottom-up: deepest level first, root last.
    Workers at the same depth level run in parallel.
    """
    print(f"\n[Phase C] Writing — {len(tree.nodes)} sections, "
          f"{len(tree.leaves())} leaves")

    worker_client = _make_client(WORKER_MODEL)

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
                client=worker_client,
            )
            result = await worker.run(
                qdrant_chunks=chunks,
                audience=audience,
                research_query=query,
            )
            print(f"    [{node.node_id}] '{node.title[:40]}' "
                  f"→ {result.word_count} words, {len(result.citations_used)} citations")

        await asyncio.gather(*[_write_node(n) for n in level_nodes])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_pipeline(
    query: str,
    strength: int = 5,
    audience: str = "practitioner",
    output_language: str = "en",
) -> str:
    """
    Full Phase 5 pipeline. Returns the final Markdown report as a string.
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

    ctx = ExecutionContext(language=output_language, depth="strength")

    vs = VectorStoreClient()

    # ── Topic cache check (triggers lazy Qdrant init + server probe) ─
    cached_run_id = vs.find_cached_run(query)   # returns None if in-memory or no hit

    if cached_run_id:
        print(f"\n[Cache HIT] Reusing collection from run {cached_run_id}")
        active_run_id = cached_run_id
        collection_name = f"run_{cached_run_id}"
        active_skills = list(SKILL_REGISTRY.keys())[:sc.retrieval_skill_count]
    else:
        # ── Phase A ───────────────────────────────────────────────────
        collection_name = vs.create_collection(run_id)   # works in-memory too
        active_run_id = run_id

        retriever = Retriever(_make_client(PLANNER_MODEL), vs)
        active_skills = await retriever.run(query, sc, run_id, collection_name, ctx)

    # ── Phase B ───────────────────────────────────────────────────────
    tree = await _phase_b(
        query=query,
        strength=sc,
        active_skills=active_skills,
        audience=audience,
    )

    # ── Phase C ───────────────────────────────────────────────────────
    await _phase_c(
        tree=tree,
        run_id=active_run_id,
        strength=sc,
        audience=audience,
        query=query,
        vs=vs,
    )

    # ── Assemble report ───────────────────────────────────────────────
    bib_md = ""
    if ctx.citation_registry:
        bib_text = ctx.citation_registry.format_bibliography()
        if bib_text.strip():
            bib_md = bib_text

    cred_avg = None
    if ctx.credibility_scores:
        cred_avg = sum(ctx.credibility_scores.values()) / len(ctx.credibility_scores)

    report_md = _format_report(tree, query, bib_md, cred_avg)

    total_words = sum(n.word_count for n in tree.nodes)
    print(f"\n{'=' * 65}")
    print("RESEARCH COMPLETE")
    print(f"  Sections written : {len(tree.nodes)}")
    print(f"  Total words      : {total_words:,}")
    print(f"  Report length    : {len(report_md):,} chars")

    return report_md
