"""
ExecutionContext — mutable state shared across all nodes in a research run.
"""
import json
import textwrap
from dataclasses import dataclass, field
from typing import Any

from .config import CREDIBILITY_ADJ
from .models import NodeStatus, PlanNode


@dataclass
class ExecutionContext:
    results: dict[str, Any]              = field(default_factory=dict)
    node_status: dict[str, NodeStatus]   = field(default_factory=dict)
    credibility_scores: dict[str, float] = field(default_factory=dict)
    prior_hashes: set[str]               = field(default_factory=set)
    language: str                        = "en"
    citation_registry: Any               = field(default=None)  # CitationRegistry; injected at run start

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
        self.results[node.output_slot] = result
        self.node_status[node.node_id] = status
        adj = CREDIBILITY_ADJ.get(fallback_level, 0.0)
        self.credibility_scores[node.output_slot] = max(0.0, credibility + adj)
        self.prior_hashes.add(node.description_hash())

    def is_resolved(self, node_id: str) -> bool:
        return node_id in self.node_status

    def result_summary(self) -> dict[str, str]:
        """Compact view of results for replanning prompts."""
        out = {}
        for slot, val in self.results.items():
            text = val if isinstance(val, str) else json.dumps(val, default=str)
            score = self.credibility_scores.get(slot, 1.0)
            summary = textwrap.shorten(text, width=350)
            if score < 0.85:
                summary += f" [credibility: {score:.2f}]"
            out[slot] = summary
        return out
