"""ExecutionContext — the shared mutable state for a single research run."""
from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass, field
from typing import Any

from .enums import NodeStatus
from .plan import PlanNode

# Credibility adjustments applied per fallback level when recording results.
CREDIBILITY_ADJ: dict[str, float] = {
    "primary":       0.0,
    "fallback_1":   -0.05,
    "fallback_2":   -0.15,
    "web_search":   -0.10,
    "forum_search": -0.20,
    "social_search":-0.25,
}


@dataclass
class ExecutionContext:
    """Mutable shared state passed through every skill and agent during a run.

    ``citation_registry`` is injected lazily to avoid a circular import between
    ``models`` and ``citations``.
    """
    results:             dict[str, Any]            = field(default_factory=dict)
    node_status:         dict[str, NodeStatus]     = field(default_factory=dict)
    credibility_scores:  dict[str, float]          = field(default_factory=dict)
    prior_hashes:        set[str]                  = field(default_factory=set)
    language:            str                       = "en"
    depth:               str                       = "standard"  # "shallow" | "standard" | "deep"
    audience:            str                       = ""
    final_output_slot:   str | None                = None
    citation_registry:   Any                       = field(default=None)

    def __post_init__(self) -> None:
        if self.citation_registry is None:
            from citations.registry import CitationRegistry
            self.citation_registry = CitationRegistry()

    def record(
        self,
        node: PlanNode,
        result: Any,
        status: NodeStatus = NodeStatus.OK,
        credibility: float = 1.0,
        fallback_level: str = "primary",
    ) -> None:
        """Store a skill result and update tracking state.

        Args:
            node:           The plan node that produced the result.
            result:         The skill's return value (a dict).
            status:         Execution status from NodeStatus enum.
            credibility:    Raw credibility score from the skill.
            fallback_level: Adjustment key into CREDIBILITY_ADJ.
        """
        self.results[node.output_slot] = result
        self.node_status[node.node_id] = status
        adj = CREDIBILITY_ADJ.get(fallback_level, 0.0)
        self.credibility_scores[node.output_slot] = max(0.0, credibility + adj)

    def is_resolved(self, node_id: str) -> bool:
        """Return True if the node has already been executed."""
        return node_id in self.node_status

    def result_summary(self) -> dict[str, str]:
        """Compact view of results suitable for replanning prompts."""
        out = {}
        for slot, val in self.results.items():
            text = val if isinstance(val, str) else json.dumps(val, default=str)
            score = self.credibility_scores.get(slot, 1.0)
            summary = textwrap.shorten(text, width=350)
            if score < 0.85:
                summary += f" [credibility: {score:.2f}]"
            out[slot] = summary
        return out
