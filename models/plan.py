"""Plan-layer data models: PlanNode."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class PlanNode:
    """A single execution node used by retrieval skills and the pipeline."""
    node_id:        str
    description:    str
    skill:          str
    depends_on:     list[str]
    acceptance:     list[str]
    parallelizable: bool
    output_slot:    str
    depth_override: str | int | None = None
    synthesis_hint: str | None       = None
    note:           str | None       = None

    def description_hash(self) -> str:
        """Short hash of (skill, description) for deduplication."""
        return hashlib.md5(f"{self.skill}:{self.description}".encode()).hexdigest()[:8]
