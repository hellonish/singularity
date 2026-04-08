"""Central data models — single source of truth for all model classes.

Package layout
--------------
models/
  enums.py    — NodeStatus
  plan.py     — PlanNode
  context.py  — ExecutionContext, CREDIBILITY_ADJ
  output.py   — SourceRecord, SourceType, RetrievalOutput, AnalysisOutput,
                 AxisResult, QualityReport, OutputFormat, OutputDocument, SkillReturn
  chunk.py    — DocumentChunk, CitationRecord

All names are re-exported here so ``from models import X`` continues to work
for every existing import site.
"""

from .enums import NodeStatus
from .plan import PlanNode
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
    "NodeStatus",
    # plan
    "PlanNode",
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
