"""
run_orchestrator — DAG-based research orchestrator (legacy path).

WHEN TO USE THIS vs run_pipeline
---------------------------------
Use ``run_orchestrator`` (this module) when:
  - Running a skill-DAG style research flow where tier-2 and tier-3 skills are
    executed directly by the FallbackRouter as plan nodes.
  - You need gap analysis → replan loops (MAX_REPLAN_ROUNDS).
  - You want the full skill registry (all 44 skills) to be accessible as
    first-class plan nodes.

Use ``run_pipeline`` (agents/orchestrator/pipeline.py) when:
  - Running the Phase 5 pipeline: plan → retrieval → vector store → writing.
  - You want the report_manager / report_lead / report_worker architecture with
    tree-structured sections, targeted retrieval per section, and Phase D polish.
  - This is the CURRENT primary production path.

Relationship: ``run_pipeline`` supersedes ``run_orchestrator`` for full research
reports.  ``run_orchestrator`` remains useful for targeted skill-DAG execution
and as a reference implementation of the replan loop.
"""
import asyncio
import json
import logging
import sys
from functools import partial
from pathlib import Path

logger = logging.getLogger(__name__)

from .config import (
    DOMAIN_CLASSIFIER_MODEL,
    MAX_NODES,
    MAX_REPLAN_ROUNDS,
    MAX_TOKENS_DOMAIN_CLASSIFIER,
    PLANNER_MODEL,
    REGISTRY_PATH,
    SKILL_PATH,
)
from .executor import execute_wave
from .fallback_router import FallbackRouter
from models import ExecutionContext, GapItem, IssueType, NodeStatus, Plan
from agents.planner import Planner, DomainRegistry
from skills import SKILL_REGISTRY

# Ensure project root is importable for the LLM client
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from llm.grok import GrokClient  # noqa: E402


# ---------------------------------------------------------------------------
# Gap analysis
# ---------------------------------------------------------------------------

def run_gap_analysis(plan: Plan, ctx: ExecutionContext) -> list[GapItem]:
    gaps: list[GapItem] = []
    for node in plan.nodes:
        status = ctx.node_status.get(node.node_id)
        if status is None:
            continue
        result = ctx.results.get(node.output_slot, {})

        if status == NodeStatus.PARTIAL:
            detail = (result.get("coverage_assessment")
                      or result.get("note")
                      or f"Node {node.node_id} returned partial status")
            gaps.append(GapItem(node.node_id, IssueType.PARTIAL, detail))

        elif status in (NodeStatus.FAILED, NodeStatus.SKIPPED):
            gaps.append(GapItem(
                node.node_id, IssueType.UNSATISFIED,
                str(result.get("error", f"Node {node.node_id} failed")),
            ))

        elif status == NodeStatus.BLOCKED:
            gaps.append(GapItem(
                node.node_id, IssueType.BLOCKED,
                f"Skill {node.skill} returned auth/access failure — cannot retry",
            ))
    return gaps


def _clear_for_reexecution(plan: Plan, ctx: ExecutionContext) -> set[str]:
    """
    After a replan, clear PARTIAL/FAILED nodes and all their transitive
    dependents so the executor treats them as unresolved and re-runs them.
    Returns the set of node_ids cleared.
    """
    to_clear = {
        node.node_id for node in plan.nodes
        if ctx.node_status.get(node.node_id) in
           (NodeStatus.PARTIAL, NodeStatus.FAILED, NodeStatus.SKIPPED, NodeStatus.BLOCKED)
    }

    # Propagate downstream: any node whose dep is cleared must also be cleared
    changed = True
    while changed:
        changed = False
        for node in plan.nodes:
            if node.node_id not in to_clear:
                if any(dep in to_clear for dep in node.depends_on):
                    to_clear.add(node.node_id)
                    changed = True

    for node in plan.nodes:
        if node.node_id in to_clear:
            ctx.node_status.pop(node.node_id, None)
            ctx.results.pop(node.output_slot, None)
            ctx.credibility_scores.pop(node.output_slot, None)

    return to_clear


def check_termination(plan: Plan, ctx: ExecutionContext) -> bool:
    all_ids = {n.node_id for n in plan.nodes}
    ok_ids  = {nid for nid, s in ctx.node_status.items()
               if s in (NodeStatus.OK, NodeStatus.OK_DEGRADED)}
    return all_ids <= ok_ids


def detect_replan_loop(plan: Plan, ctx: ExecutionContext) -> list[str]:
    """Return node_ids whose (skill + description) hash matches a prior failed attempt."""
    return [
        node.node_id for node in plan.nodes
        if (node.description_hash() in ctx.prior_hashes
            and ctx.node_status.get(node.node_id)
            not in (NodeStatus.OK, NodeStatus.OK_DEGRADED))
    ]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

OUTPUT_SKILLS = {"report_generator", "exec_summary", "explainer",
                 "decision_matrix", "knowledge_delta"}

_DEPTH_LIMITS: dict[str, dict] = {
    "shallow":  {"rounds": 1, "max_nodes": 8},
    "standard": {"rounds": 3, "max_nodes": 15},
    "deep":     {"rounds": 5, "max_nodes": 25},
}


async def run_orchestrator(
    problem_statement: str,
    audience: str = "",
    output_language: str = "en",
    depth: str = "standard",
) -> ExecutionContext:
    limits   = _DEPTH_LIMITS.get(depth, _DEPTH_LIMITS["standard"])
    classifier_client = GrokClient(model_name=DOMAIN_CLASSIFIER_MODEL)
    client = GrokClient(model_name=PLANNER_MODEL)
    registry = DomainRegistry(REGISTRY_PATH)
    planner = Planner(SKILL_PATH, client)
    router = FallbackRouter(registry, SKILL_REGISTRY)
    ctx = ExecutionContext(language=output_language, depth=depth)

    detected_domain, confidence = await asyncio.to_thread(
        partial(
            registry.detect_domain_llm,
            problem_statement,
            classifier_client,
            max_tokens=MAX_TOKENS_DOMAIN_CLASSIFIER,
        )
    )
    domain_info = registry.get_domain(detected_domain)

    logger.info("=" * 65)
    logger.info("RESEARCH AGENT v2.0 — UNIVERSAL DOMAIN-ADAPTIVE")
    logger.info("=" * 65)
    logger.info("\nProblem  : %s", problem_statement)
    logger.info("Domain   : %s (pre-detected, confidence=%s)", domain_info["label"], confidence)
    logger.info("Audience : %s", audience or "auto-detect")
    logger.info("Language : %s", output_language)
    logger.info("Depth    : %s  (rounds=%d, max_nodes=%d)\n", depth, limits["rounds"], limits["max_nodes"])

    # ── Initial plan ──────────────────────────────────────────────
    logger.info("[Round 0] Calling planner...")
    _, plan = planner.plan(
        problem_statement,
        audience,
        output_language,
        depth,
        preclassified_domain=detected_domain,
        domain_confidence=confidence,
    )
    ctx.audience = plan.metadata.audience
    logger.info("  Goal     : %s", plan.metadata.core_goal)
    logger.info("  Domain   : %s", plan.metadata.domain)
    logger.info("  Audience : %s", plan.metadata.audience)
    logger.info("  Type     : %s", plan.metadata.research_type)
    logger.info("  Nodes    : %s", plan.metadata.node_count)
    logger.info("  Sensitive: %s", plan.metadata.sensitivity_flag)
    logger.info("  Terminal : %s", plan.metadata.termination_signal)

    if plan.has_cycle():
        logger.error("[ERROR] Planner produced a cyclic DAG — halting.")
        return ctx

    # ── Execution rounds ──────────────────────────────────────────
    for round_num in range(1, limits["rounds"] + 1):
        logger.info("\n%s", "─" * 65)
        logger.info("[Round %d] Executing plan (%d nodes)", round_num, len(plan.nodes))

        try:
            waves = plan.topological_waves()
        except ValueError as exc:
            logger.error("  [ERROR] %s", exc)
            break

        for wave_idx, wave in enumerate(waves):
            await execute_wave(wave, ctx, client, router, wave_idx)

        # ── Gap analysis ───────────────────────────────────────────
        gaps = run_gap_analysis(plan, ctx)
        logger.info("\n[Round %d] Gap analysis: %d issue(s)", round_num, len(gaps))
        for g in gaps:
            logger.info("  %s [%s]: %s", g.node_id, g.issue.value, g.detail[:75])

        if check_termination(plan, ctx) and not gaps:
            logger.info("\n[Round %d] Termination signal met — research complete.", round_num)
            break

        if round_num >= limits["rounds"]:
            logger.info("\n[Round %d] Max replan rounds reached.", round_num)
            break

        # Snapshot failing node hashes BEFORE replanning so the next round
        # can detect if the replan generates the same failing nodes again.
        for node in plan.nodes:
            s = ctx.node_status.get(node.node_id)
            if s not in (NodeStatus.OK, NodeStatus.OK_DEGRADED, None):
                ctx.prior_hashes.add(node.description_hash())

        # ── Replan ────────────────────────────────────────────────
        logger.info("\n[Round %d] Replanning...", round_num)
        _, plan = planner.replan(problem_statement, ctx, gaps, round_num, depth)

        looping = detect_replan_loop(plan, ctx)
        if looping:
            logger.warning("\n[WARN] Replan loop detected on %s — stopping with partial results.", looping)
            break

        # Clear partial/failed nodes (and their dependents) so the next round
        # actually re-executes them instead of treating them as resolved.
        cleared = _clear_for_reexecution(plan, ctx)
        if cleared:
            logger.info("  Cleared for re-execution: %s", sorted(cleared))

        if plan.metadata.node_count > limits["max_nodes"]:
            logger.warning("  [WARN] Clamping plan from %d → %d nodes.", plan.metadata.node_count, limits["max_nodes"])
            plan.nodes = plan.nodes[:limits["max_nodes"]]

        if plan.has_cycle():
            logger.error("  [ERROR] Replan produced a cyclic DAG — stopping.")
            break

        logger.info("  New plan: %d nodes (replan round %d)", len(plan.nodes), round_num)

    # ── Final summary ──────────────────────────────────────────────
    ok_count   = sum(1 for s in ctx.node_status.values() if s in (NodeStatus.OK, NodeStatus.OK_DEGRADED))
    fail_count = sum(1 for s in ctx.node_status.values() if s in (NodeStatus.FAILED, NodeStatus.SKIPPED))
    logger.info("\n%s", "=" * 65)
    logger.info("RESEARCH COMPLETE")
    logger.info("  Nodes OK     : %d", ok_count)
    logger.info("  Nodes failed : %d", fail_count)
    logger.info("  Output slots : %s", list(ctx.results.keys()))

    final_node = next((n for n in reversed(plan.nodes) if n.skill in OUTPUT_SKILLS), None)
    if final_node and final_node.output_slot in ctx.results:
        ctx.final_output_slot = final_node.output_slot
        logger.info("\nFinal output slot: '%s'", final_node.output_slot)
        logger.info(json.dumps(ctx.results[final_node.output_slot], indent=2, default=str))

    if ctx.credibility_scores:
        avg = sum(ctx.credibility_scores.values()) / len(ctx.credibility_scores)
        logger.info("\nMean source credibility: %.2f", avg)

    return ctx
