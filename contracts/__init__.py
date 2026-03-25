"""
contracts/ — Skill I/O Contracts (Phase 0B).

Import from here in skills and tests. Never import directly from skill_contracts.
"""
from .skill_contracts import (
    # Types / aliases
    SourceType,
    OutputFormat,
    SkillReturn,
    # Tier 1
    SourceRecord,
    RetrievalOutput,
    # Tier 2
    AnalysisOutput,
    AxisResult,
    QualityReport,
    # Tier 3
    OutputDocument,
)

__all__ = [
    "SourceType",
    "OutputFormat",
    "SkillReturn",
    "SourceRecord",
    "RetrievalOutput",
    "AnalysisOutput",
    "AxisResult",
    "QualityReport",
    "OutputDocument",
]
