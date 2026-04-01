"""Central data models — single source of truth for all model classes.

Package layout
--------------
models/
  enums.py    — IssueType, NodeStatus
  plan.py     — GapItem, PlanNode, PlanMetadata, Plan
  context.py  — ExecutionContext, CREDIBILITY_ADJ
  output.py   — SourceRecord, SourceType, RetrievalOutput, AnalysisOutput,
                 AxisResult, QualityReport, OutputFormat, OutputDocument, SkillReturn
  chunk.py    — DocumentChunk, CitationRecord

All names are re-exported here so ``from models import X`` continues to work
for every existing import site.
"""

from .enums import IssueType, NodeStatus
from .plan import GapItem, PlanNode, PlanMetadata, Plan
from .context import ExecutionContext, CREDIBILITY_ADJ
from .output import (
    SourceType,
    SourceRecord,
    RetrievalOutput,
    AnalysisOutput,
    AxisResult,
    QualityReport,
    OutputFormat,
    OutputDocument,
    SkillReturn,
)
from .chunk import DocumentChunk, CitationRecord

__all__ = [
    # enums
    "IssueType",
    "NodeStatus",
    # plan
    "GapItem",
    "PlanNode",
    "PlanMetadata",
    "Plan",
    # context
    "ExecutionContext",
    "CREDIBILITY_ADJ",
    # output
    "SourceType",
    "SourceRecord",
    "RetrievalOutput",
    "AnalysisOutput",
    "AxisResult",
    "QualityReport",
    "OutputFormat",
    "OutputDocument",
    "SkillReturn",
    # chunk
    "DocumentChunk",
    "CitationRecord",
]
