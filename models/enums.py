"""Shared enumerations used across all tiers and the orchestrator."""
from __future__ import annotations

from enum import Enum


class IssueType(str, Enum):
    """Classification of an unresolved plan node (used by gap analysis)."""
    UNSATISFIED   = "unsatisfied"
    PARTIAL       = "partial"
    CONTRADICTORY = "contradictory"
    BLOCKED       = "blocked"


class NodeStatus(str, Enum):
    """Execution status reported by every skill's run() method."""
    OK          = "ok"
    OK_DEGRADED = "ok_degraded"
    PARTIAL     = "partial"
    FAILED      = "failed"
    SKIPPED     = "skipped"
    BLOCKED     = "blocked"
