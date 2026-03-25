"""
Core data models: enums, plan nodes, and the Plan DAG.
"""
import hashlib
from dataclasses import dataclass
from enum import Enum


class IssueType(str, Enum):
    UNSATISFIED   = "unsatisfied"
    PARTIAL       = "partial"
    CONTRADICTORY = "contradictory"
    BLOCKED       = "blocked"


class NodeStatus(str, Enum):
    OK          = "ok"
    OK_DEGRADED = "ok_degraded"
    PARTIAL     = "partial"
    FAILED      = "failed"
    SKIPPED     = "skipped"
    BLOCKED     = "blocked"


@dataclass
class GapItem:
    node_id: str
    issue: IssueType
    detail: str


@dataclass
class PlanNode:
    node_id: str
    description: str
    skill: str
    depends_on: list[str]
    acceptance: list[str]
    parallelizable: bool
    output_slot: str
    depth_override: str | None = None
    synthesis_hint: str | None = None
    note: str | None = None

    def description_hash(self) -> str:
        return hashlib.md5(f"{self.skill}:{self.description}".encode()).hexdigest()[:8]


@dataclass
class PlanMetadata:
    research_type: str
    core_goal: str
    domain: str
    audience: str
    output_format: str
    output_language: str
    depth_default: str
    recency_window_years: float
    termination_signal: str
    node_count: int
    sensitivity_flag: bool
    multilingual: bool
    created_at_mode: str
    replan_round: int


@dataclass
class Plan:
    metadata: PlanMetadata
    nodes: list[PlanNode]

    def node_by_id(self, node_id: str) -> PlanNode | None:
        return next((n for n in self.nodes if n.node_id == node_id), None)

    def topological_waves(self) -> list[list[PlanNode]]:
        """Group nodes into parallel execution waves respecting deps. Raises on cycle."""
        remaining = {n.node_id: n for n in self.nodes}
        resolved: set[str] = set()
        waves: list[list[PlanNode]] = []
        while remaining:
            wave = [n for n in remaining.values()
                    if all(d in resolved for d in n.depends_on)]
            if not wave:
                raise ValueError(
                    f"DAG cycle or unresolvable deps. Stuck: {list(remaining.keys())}")
            waves.append(wave)
            for n in wave:
                resolved.add(n.node_id)
                del remaining[n.node_id]
        return waves

    def has_cycle(self) -> bool:
        adj = {n.node_id: set(n.depends_on) for n in self.nodes}
        visited, stack = set(), set()

        def dfs(nid: str) -> bool:
            visited.add(nid)
            stack.add(nid)
            for dep in adj.get(nid, set()):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in stack:
                    return True
            stack.discard(nid)
            return False

        return any(dfs(n.node_id) for n in self.nodes if n.node_id not in visited)
