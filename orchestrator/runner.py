"""
run_orchestrator — top-level entry point for a research run.
Also contains gap analysis, termination check, and loop detection helpers.
"""
import json
import sys
from pathlib import Path

from .config import MAX_NODES, MAX_REPLAN_ROUNDS, PLANNER_MODEL, REGISTRY_PATH, SKILL_PATH
from .context import ExecutionContext
from .domain import DomainRegistry
from .executor import FallbackRouter, execute_wave
from .models import GapItem, IssueType, NodeStatus, Plan
from .planner import Planner
from .skills import SKILL_REGISTRY

# Ensure project root is importable for the LLM client
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
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
    client   = GrokClient(model_name=PLANNER_MODEL)
    registry = DomainRegistry(REGISTRY_PATH)
    planner  = Planner(SKILL_PATH, client)
    router   = FallbackRouter(registry, SKILL_REGISTRY)
    ctx      = ExecutionContext(language=output_language, depth=depth)

    detected_domain, confidence = registry.detect_domain(problem_statement)
    domain_info = registry.get_domain(detected_domain)

    print("=" * 65)
    print("RESEARCH AGENT v2.0 — UNIVERSAL DOMAIN-ADAPTIVE")
    print("=" * 65)
    print(f"\nProblem  : {problem_statement}")
    print(f"Domain   : {domain_info['label']} (pre-detected, confidence={confidence})")
    print(f"Audience : {audience or 'auto-detect'}")
    print(f"Language : {output_language}")
    print(f"Depth    : {depth}  (rounds={limits['rounds']}, max_nodes={limits['max_nodes']})\n")

    # ── Initial plan ──────────────────────────────────────────────
    print("[Round 0] Calling planner...")
    _, plan = planner.plan(problem_statement, audience, output_language, depth)
    ctx.audience = plan.metadata.audience
    print(f"  Goal     : {plan.metadata.core_goal}")
    print(f"  Domain   : {plan.metadata.domain}")
    print(f"  Audience : {plan.metadata.audience}")
    print(f"  Type     : {plan.metadata.research_type}")
    print(f"  Nodes    : {plan.metadata.node_count}")
    print(f"  Sensitive: {plan.metadata.sensitivity_flag}")
    print(f"  Terminal : {plan.metadata.termination_signal}")

    if plan.has_cycle():
        print("[ERROR] Planner produced a cyclic DAG — halting.")
        return ctx

    # ── Execution rounds ──────────────────────────────────────────
    for round_num in range(1, limits["rounds"] + 1):
        print(f"\n{'─' * 65}")
        print(f"[Round {round_num}] Executing plan ({len(plan.nodes)} nodes)")

        try:
            waves = plan.topological_waves()
        except ValueError as exc:
            print(f"  [ERROR] {exc}")
            break

        for wave_idx, wave in enumerate(waves):
            await execute_wave(wave, ctx, client, router, wave_idx)

        # ── Gap analysis ───────────────────────────────────────────
        gaps = run_gap_analysis(plan, ctx)
        print(f"\n[Round {round_num}] Gap analysis: {len(gaps)} issue(s)")
        for g in gaps:
            print(f"  {g.node_id} [{g.issue.value}]: {g.detail[:75]}")

        if check_termination(plan, ctx) and not gaps:
            print(f"\n[Round {round_num}] Termination signal met — research complete.")
            break

        if round_num >= limits["rounds"]:
            print(f"\n[Round {round_num}] Max replan rounds reached.")
            break

        # Snapshot failing node hashes BEFORE replanning so the next round
        # can detect if the replan generates the same failing nodes again.
        for node in plan.nodes:
            s = ctx.node_status.get(node.node_id)
            if s not in (NodeStatus.OK, NodeStatus.OK_DEGRADED, None):
                ctx.prior_hashes.add(node.description_hash())

        # ── Replan ────────────────────────────────────────────────
        print(f"\n[Round {round_num}] Replanning...")
        _, plan = planner.replan(problem_statement, ctx, gaps, round_num, depth)

        looping = detect_replan_loop(plan, ctx)
        if looping:
            print(f"\n[WARN] Replan loop detected on {looping} — stopping with partial results.")
            break

        if plan.metadata.node_count > limits["max_nodes"]:
            print(f"  [WARN] Clamping plan from {plan.metadata.node_count} → {limits['max_nodes']} nodes.")
            plan.nodes = plan.nodes[:limits["max_nodes"]]

        if plan.has_cycle():
            print("  [ERROR] Replan produced a cyclic DAG — stopping.")
            break

        print(f"  New plan: {len(plan.nodes)} nodes (replan round {round_num})")

    # ── Final summary ──────────────────────────────────────────────
    ok_count   = sum(1 for s in ctx.node_status.values() if s in (NodeStatus.OK, NodeStatus.OK_DEGRADED))
    fail_count = sum(1 for s in ctx.node_status.values() if s in (NodeStatus.FAILED, NodeStatus.SKIPPED))
    print(f"\n{'=' * 65}")
    print("RESEARCH COMPLETE")
    print(f"  Nodes OK     : {ok_count}")
    print(f"  Nodes failed : {fail_count}")
    print(f"  Output slots : {list(ctx.results.keys())}")

    final_node = next((n for n in reversed(plan.nodes) if n.skill in OUTPUT_SKILLS), None)
    if final_node and final_node.output_slot in ctx.results:
        print(f"\nFinal output slot: '{final_node.output_slot}'")
        print(json.dumps(ctx.results[final_node.output_slot], indent=2, default=str))

    if ctx.credibility_scores:
        avg = sum(ctx.credibility_scores.values()) / len(ctx.credibility_scores)
        print(f"\nMean source credibility: {avg:.2f}")

    return ctx
