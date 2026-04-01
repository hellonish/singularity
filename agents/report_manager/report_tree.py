"""
ReportTree — hierarchical section tree and helper functions.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from .section_node import SectionNode
from utils.json_parser import extract_object


@dataclass
class ReportTree:
    nodes:       list[SectionNode]     # flat list, ordered by node_id
    proposal_id: str
    rationale:   str
    total_nodes: int

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def root(self) -> SectionNode:
        return next(n for n in self.nodes if n.parent_id is None)

    @property
    def max_depth(self) -> int:
        return max(n.level for n in self.nodes)

    def children_of(self, node_id: str) -> list[SectionNode]:
        return [n for n in self.nodes if n.parent_id == node_id]

    def leaves(self) -> list[SectionNode]:
        ids_with_children = {n.parent_id for n in self.nodes if n.parent_id}
        return [n for n in self.nodes if n.node_id not in ids_with_children]

    def nodes_at_level(self, level: int) -> list[SectionNode]:
        return [n for n in self.nodes if n.level == level]

    def by_id(self, node_id: str) -> SectionNode | None:
        return next((n for n in self.nodes if n.node_id == node_id), None)

    def topological_levels(self) -> list[list[SectionNode]]:
        """Return nodes grouped by level, deepest first (bottom-up for workers)."""
        levels: dict[int, list[SectionNode]] = {}
        for n in self.nodes:
            levels.setdefault(n.level, []).append(n)
        return [levels[d] for d in sorted(levels.keys(), reverse=True)]

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "rationale":   self.rationale,
            "total_nodes": self.total_nodes,
            "tree": [
                {
                    "node_id":      n.node_id,
                    "parent_id":    n.parent_id,
                    "level":        n.level,
                    "title":        n.title,
                    "description":  n.description,
                    "section_type": n.section_type,
                }
                for n in self.nodes
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportTree":
        nodes = [
            SectionNode(
                node_id=n["node_id"],
                parent_id=n.get("parent_id"),
                level=n["level"],
                title=n["title"],
                description=n["description"],
                section_type=n.get("section_type", "section"),
                requires_fresh=bool(n.get("requires_fresh", False)),
            )
            for n in data["tree"]
        ]
        return cls(
            nodes=nodes,
            proposal_id=data.get("proposal_id", ""),
            rationale=data.get("rationale", ""),
            total_nodes=len(nodes),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any]:
    result = extract_object(text)
    if result is not None:
        return result
    raise ValueError(f"No JSON found in manager response (first 300 chars):\n{text.strip()[:300]}")


def _enforce_node_count(tree: ReportTree, target_n: int) -> ReportTree:
    """
    Hard-enforce the node count without touching structure.
    - Too many nodes: trim from deepest level, highest index first.
    - Too few nodes: duplicate deepest-level leaf nodes with "(cont.)" suffix
      until count is met. This is a last-resort fallback — the LLM should count
      correctly given the prompt instruction.
    """
    nodes = list(tree.nodes)
    diff = len(nodes) - target_n

    if diff > 0:
        # Remove excess nodes (deepest, last first)
        sorted_nodes = sorted(nodes, key=lambda n: (-n.level, n.node_id), reverse=False)
        # Be careful not to remove parents — only remove true leaves
        leaf_ids = {n.node_id for n in nodes} - {n.parent_id for n in nodes if n.parent_id}
        removable = [n for n in sorted_nodes if n.node_id in leaf_ids]
        to_remove = {n.node_id for n in removable[:diff]}
        nodes = [n for n in nodes if n.node_id not in to_remove]

    elif diff < 0:
        # Add stub subsections under existing leaves
        leaf_ids = {n.node_id for n in nodes} - {n.parent_id for n in nodes if n.parent_id}
        leaves = [n for n in nodes if n.node_id in leaf_ids]
        idx = 0
        while len(nodes) < target_n:
            parent = leaves[idx % len(leaves)]
            stub = SectionNode(
                node_id=f"stub_{uuid.uuid4().hex[:6]}",
                parent_id=parent.node_id,
                level=parent.level + 1,
                title=f"{parent.title} (continued)",
                description=f"Additional detail for '{parent.title}'",
                section_type="subsection",
            )
            nodes.append(stub)
            idx += 1

    return ReportTree(
        nodes=nodes,
        proposal_id=tree.proposal_id,
        rationale=tree.rationale,
        total_nodes=len(nodes),
    )
