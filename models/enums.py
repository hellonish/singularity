"""Shared enumerations used across all tiers and the pipeline."""
from __future__ import annotations

from enum import Enum


class NodeStatus(str, Enum):
    """Execution status reported by every skill's run() method."""
    OK          = "ok"
    OK_DEGRADED = "ok_degraded"
    PARTIAL     = "partial"
    FAILED      = "failed"
    SKIPPED     = "skipped"
    BLOCKED     = "blocked"
