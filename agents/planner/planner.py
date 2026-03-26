"""
Planner — calls the LLM with PLANNER.md as system prompt to produce a DAG plan,
and parse_plan converts the raw LLM output into a typed Plan object.
"""
import json
import re
from pathlib import Path

from models import ExecutionContext, GapItem, Plan, PlanMetadata, PlanNode


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _find_dag_block(obj, _depth: int = 0) -> dict | None:
    """
    Recursively search any parsed JSON value for a dict that has both
    'nodes' (a list) and 'metadata' (a dict). Works at any nesting depth.
    """
    if _depth > 8:
        return None
    if isinstance(obj, dict):
        if isinstance(obj.get("nodes"), list) and isinstance(obj.get("metadata"), dict):
            return obj
        for val in obj.values():
            hit = _find_dag_block(val, _depth + 1)
            if hit:
                return hit
    elif isinstance(obj, list):
        for item in obj:
            hit = _find_dag_block(item, _depth + 1)
            if hit:
                return hit
    return None


def parse_plan(markdown: str) -> Plan:
    """Extract the JSON DAG block from the planner's raw Markdown response."""
    dag_block: dict | None = None
    _decoder = json.JSONDecoder()

    def _try_parse(text: str) -> dict | None:
        """Try json.loads then raw_decode; return _find_dag_block result or None."""
        for loader in (
            lambda t: json.loads(t),
            lambda t: _decoder.raw_decode(t)[0],
        ):
            try:
                parsed = loader(text)
                hit = _find_dag_block(parsed)
                if hit:
                    return hit
            except (json.JSONDecodeError, ValueError):
                continue
        return None

    # Strategy 1: any fenced ```json block in the response
    for raw_block in re.findall(r"```(?:json)?\s*\n(.*?)\n```", markdown, re.DOTALL):
        dag_block = _try_parse(raw_block.strip())
        if dag_block:
            break

    # Strategy 2: the whole text is / starts with a JSON object
    if not dag_block:
        dag_block = _try_parse(markdown.strip())

    # Strategy 3: scan every `{` position and try parsing from there.
    # Catches cases where the outer JSON is malformed but an inner object is valid.
    if not dag_block:
        for m in re.finditer(r'\{', markdown):
            try:
                candidate, _ = _decoder.raw_decode(markdown, m.start())
                dag_block = _find_dag_block(candidate)
                if dag_block:
                    break
            except (json.JSONDecodeError, ValueError):
                continue

    if dag_block is None:
        raise ValueError(
            f"No valid DAG JSON block found in planner output.\n"
            f"First 600 chars:\n{markdown[:600]}"
        )

    m = dag_block["metadata"]
    meta = PlanMetadata(
        research_type        = m.get("research_type", "exploratory"),
        core_goal            = m.get("core_goal", ""),
        domain               = m.get("domain", "general"),
        audience             = m.get("audience", "practitioner"),
        output_format        = m.get("output_format", "report"),
        output_language      = m.get("output_language", "en"),
        depth_default        = m.get("depth_default", "deep"),
        recency_window_years = float(m.get("recency_window_years", 3)),
        termination_signal   = m.get("termination_signal", ""),
        node_count           = m.get("node_count", len(dag_block["nodes"])),
        sensitivity_flag     = bool(m.get("sensitivity_flag", False)),
        multilingual         = bool(m.get("multilingual", False)),
        created_at_mode      = m.get("created_at_mode", "plan"),
        replan_round         = int(m.get("replan_round", 0)),
    )
    nodes = [
        PlanNode(
            node_id        = n["node_id"],
            description    = n["description"],
            skill          = n["skill"],
            depends_on     = n.get("depends_on", []),
            acceptance     = n.get("acceptance", []),
            parallelizable = n.get("parallelizable", True),
            output_slot    = n["output_slot"],
            depth_override = n.get("depth_override"),
            synthesis_hint = n.get("synthesis_hint"),
            note           = n.get("note"),
        )
        for n in dag_block["nodes"]
    ]
    return Plan(metadata=meta, nodes=nodes)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class Planner:
    def __init__(self, skill_path: Path, client):
        self.skill_md = skill_path.read_text(encoding="utf-8")
        self.client = client

    def _call(self, user_content: str) -> str:
        raw = self.client.generate_text(
            prompt=user_content,
            system_prompt=self.skill_md,
            temperature=0.2,
        )
        from agents.orchestrator.config import PLANNER_OUTPUT
        PLANNER_OUTPUT.write_text(raw, encoding="utf-8")
        print(f"  [planner] Raw output saved → {PLANNER_OUTPUT}")
        return raw

    # ------------------------------------------------------------------
    # Depth → planner directive
    # ------------------------------------------------------------------

    _DEPTH_DIRECTIVE: dict[str, str] = {
        "shallow": (
            "depth: shallow\n"
            "depth_guidance: Generate 3–5 nodes. Cover 1–2 perspectives. "
            "Set depth_override='shallow' on all retrieval nodes. "
            "Prioritise speed and breadth over exhaustive coverage."
        ),
        "standard": (
            "depth: standard\n"
            "depth_guidance: Generate 7–10 nodes. Cover 3–4 distinct perspectives. "
            "Set depth_override='standard' on retrieval nodes."
        ),
        "deep": (
            "depth: deep\n"
            "depth_guidance: Generate 15–20 nodes. Cover 5+ distinct perspectives and "
            "sub-topics. Set depth_override='deep' on all retrieval nodes. "
            "Include meta_analysis, contradiction_detect, and claim_verification as "
            "analysis nodes to maximise evidence quality."
        ),
    }

    def plan(
        self,
        problem: str,
        audience: str = "",
        output_language: str = "en",
        depth: str = "standard",
    ) -> tuple[str, Plan]:
        parts = ["mode: plan", f"problem_statement: {problem}"]
        if audience:
            parts.append(f"audience: {audience}")
        if output_language and output_language != "en":
            parts.append(f"output_language: {output_language}")
        parts.append(self._DEPTH_DIRECTIVE.get(depth, self._DEPTH_DIRECTIVE["standard"]))
        raw = self._call("\n".join(parts))
        return raw, parse_plan(raw)

    def replan(
        self,
        problem: str,
        ctx: ExecutionContext,
        gaps: list[GapItem],
        round_num: int,
        depth: str = "standard",
    ) -> tuple[str, Plan]:
        gap_list = [
            {"node_id": g.node_id, "issue": g.issue.value, "detail": g.detail}
            for g in gaps
        ]
        ctx_block = json.dumps(
            {"execution_results": ctx.result_summary(), "gap_report": gap_list},
            indent=2,
        )
        raw = self._call(
            f"mode: replan\n"
            f"problem_statement: {problem}\n"
            f"replan_round: {round_num}\n"
            f"{self._DEPTH_DIRECTIVE.get(depth, self._DEPTH_DIRECTIVE['standard'])}\n"
            f"context:\n{ctx_block}"
        )
        return raw, parse_plan(raw)
