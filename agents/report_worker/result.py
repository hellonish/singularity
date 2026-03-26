"""
WorkerResult — the output of a single ReportWorkerAgent execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkerResult:
    node_id:      str
    section_title: str
    content:      str
    word_count:   int
    node_type:    str                   # "leaf" | "parent"
    tier2_used:   list[str]
    tier3_used:   str
    citations_used: list[str]
    qdrant_chunks_used: list[int]       # chunk indices referenced
    children_consumed: list[str]        # node_ids of children (parent workers only)
    coverage_gaps: list[str] = field(default_factory=list)
    source_map: dict = field(default_factory=dict)  # citation_id → {title, url}
