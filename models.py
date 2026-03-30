"""
Central data models — single source of truth for all model classes.

Combines:
  - orchestrator/models.py:    IssueType, NodeStatus, GapItem, PlanNode, PlanMetadata, Plan
  - orchestrator/context.py:   ExecutionContext
  - contracts/skill_contracts.py: SourceType, SourceRecord, RetrievalOutput, AnalysisOutput,
                                   AxisResult, QualityReport, OutputFormat, OutputDocument, SkillReturn
  - vector_store/schema.py:    DocumentChunk
  - citations/registry.py:     CitationRecord (CitationRegistry stays in citations/registry.py)
"""
from __future__ import annotations

import hashlib
import json
import textwrap
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Credibility adjustments per fallback level (inlined from orchestrator/config.py)
# ---------------------------------------------------------------------------

CREDIBILITY_ADJ: dict[str, float] = {
    "primary":       0.0,
    "fallback_1":   -0.05,
    "fallback_2":   -0.15,
    "web_search":   -0.10,
    "forum_search": -0.20,
    "social_search":-0.25,
}


# ---------------------------------------------------------------------------
# Enums — from orchestrator/models.py
# ---------------------------------------------------------------------------

class IssueType(str, Enum):
    UNSATISFIED   = "unsatisfied"
    PARTIAL       = "partial"
    CONTRADICTORY = "contradictory"
    BLOCKED       = "blocked"


class NodeStatus(str, Enum):
    OK          = "ok"
    OK_DEGRADED = "ok_degraded"
    PARTIAL     = "partial"
    FAILED      = "failed"
    SKIPPED     = "skipped"
    BLOCKED     = "blocked"


# ---------------------------------------------------------------------------
# Plan models — from orchestrator/models.py
# ---------------------------------------------------------------------------

@dataclass
class GapItem:
    node_id: str
    issue: IssueType
    detail: str


@dataclass
class PlanNode:
    node_id: str
    description: str
    skill: str
    depends_on: list[str]
    acceptance: list[str]
    parallelizable: bool
    output_slot: str
    depth_override: str | int | None = None
    synthesis_hint: str | None = None
    note: str | None = None

    def description_hash(self) -> str:
        return hashlib.md5(f"{self.skill}:{self.description}".encode()).hexdigest()[:8]


@dataclass
class PlanMetadata:
    research_type: str
    core_goal: str
    domain: str
    audience: str
    output_format: str
    output_language: str
    depth_default: str
    recency_window_years: float
    termination_signal: str
    node_count: int
    sensitivity_flag: bool
    multilingual: bool
    created_at_mode: str
    replan_round: int


@dataclass
class Plan:
    metadata: PlanMetadata
    nodes: list[PlanNode]

    def node_by_id(self, node_id: str) -> PlanNode | None:
        return next((n for n in self.nodes if n.node_id == node_id), None)

    def topological_waves(self) -> list[list[PlanNode]]:
        """Group nodes into parallel execution waves respecting deps. Raises on cycle."""
        remaining = {n.node_id: n for n in self.nodes}
        resolved: set[str] = set()
        waves: list[list[PlanNode]] = []
        while remaining:
            wave = [n for n in remaining.values()
                    if all(d in resolved for d in n.depends_on)]
            if not wave:
                raise ValueError(
                    f"DAG cycle or unresolvable deps. Stuck: {list(remaining.keys())}")
            waves.append(wave)
            for n in wave:
                resolved.add(n.node_id)
                del remaining[n.node_id]
        return waves

    def has_cycle(self) -> bool:
        adj = {n.node_id: set(n.depends_on) for n in self.nodes}
        visited, stack = set(), set()

        def dfs(nid: str) -> bool:
            visited.add(nid)
            stack.add(nid)
            for dep in adj.get(nid, set()):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in stack:
                    return True
            stack.discard(nid)
            return False

        return any(dfs(n.node_id) for n in self.nodes if n.node_id not in visited)


# ---------------------------------------------------------------------------
# ExecutionContext — from orchestrator/context.py
# ---------------------------------------------------------------------------

@dataclass
class ExecutionContext:
    results: dict[str, Any]              = field(default_factory=dict)
    node_status: dict[str, NodeStatus]   = field(default_factory=dict)
    credibility_scores: dict[str, float] = field(default_factory=dict)
    prior_hashes: set[str]               = field(default_factory=set)
    language: str                        = "en"
    depth: str                           = "standard"  # "shallow" | "standard" | "deep"
    audience: str                        = ""
    final_output_slot: str | None        = None  # Set by runner after identifying the report node
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


# ---------------------------------------------------------------------------
# Source types — from contracts/skill_contracts.py
# ---------------------------------------------------------------------------

SourceType = Literal[
    "academic", "web", "gov", "forum", "legal",
    "clinical", "financial", "code", "book",
    "video", "standard", "patent", "dataset",
    "pdf", "translation",
]

# ---------------------------------------------------------------------------
# SourceRecord — produced by all tier 1 retrieval skills
# ---------------------------------------------------------------------------

class SourceRecord(BaseModel):
    """
    A single retrieved source. Created by tier 1 skills, referenced by
    citation_id in all downstream tiers.

    citation_id is empty ("") until CitationRegistry.register() assigns one.
    """
    model_config = ConfigDict(frozen=True)

    citation_id:      str        = Field(default="", description="Assigned by CitationRegistry e.g. [Smith2024]")
    title:            str
    url:              str
    snippet:          str        = Field(description="200-300 char extract from the source")
    date:             str | None = Field(default=None, description="ISO date YYYY-MM-DD")
    source_type:      SourceType
    credibility_base: float      = Field(ge=0.0, le=1.0)
    authors:          list[str]  = Field(default_factory=list)
    metadata:         dict       = Field(default_factory=dict, description="Skill-specific extra fields")

    @field_validator("snippet")
    @classmethod
    def truncate_snippet(cls, v: str) -> str:
        return v[:300]

    @classmethod
    def from_tool_dict(cls, d: dict, source_type: SourceType) -> "SourceRecord":
        """
        Convenience factory — converts a raw dict from the tools layer
        (e.g. a single entry from ToolResult.sources) into a SourceRecord.
        """
        return cls(
            title            = d.get("title", ""),
            url              = d.get("url", ""),
            snippet          = (d.get("snippet") or "")[:300],
            date             = d.get("date"),
            source_type      = d.get("source_type", source_type),
            credibility_base = float(d.get("credibility_base", 0.75)),
            authors          = d.get("authors", []),
            metadata         = d.get("metadata", {}),
        )

    def with_citation_id(self, citation_id: str) -> "SourceRecord":
        """Return a new SourceRecord with the citation_id assigned."""
        return self.model_copy(update={"citation_id": citation_id})

    def to_dict(self) -> dict:
        return self.model_dump()


# ---------------------------------------------------------------------------
# Tier 1 — RetrievalOutput
# ---------------------------------------------------------------------------

class RetrievalOutput(BaseModel):
    """Output contract for all 18 tier 1 retrieval skills."""
    model_config = ConfigDict(frozen=True)

    skill_name:     str
    sources:        list[SourceRecord]
    query_used:     str
    result_count:   int
    coverage_notes: str  = Field(description="e.g. '6 results found; 2 excluded for recency'")
    fallback_used:  bool = False

    @field_validator("result_count", mode="before")
    @classmethod
    def sync_result_count(cls, v: int, info) -> int:
        # Allow caller to pass 0 and have it computed from sources length
        return v

    def to_dict(self) -> dict:
        d = self.model_dump()
        d["sources"] = [s.to_dict() for s in self.sources]
        return d


# ---------------------------------------------------------------------------
# Tier 2 — AnalysisOutput (base for all analysis skills)
# ---------------------------------------------------------------------------

class AnalysisOutput(BaseModel):
    """
    Base output contract for tier 2 analysis skills.

    Each skill fills `findings` with its own structure — document the
    exact finding schema in the skill's module docstring.
    """
    model_config = ConfigDict(frozen=True)

    skill_name:               str
    summary:                  str        = Field(description="2-4 sentence human-readable summary")
    findings:                 list[dict] = Field(description="Skill-specific structured findings list")
    citations_used:           list[str]  = Field(description="citation_ids referenced e.g. ['[Smith2024]']")
    confidence:               float      = Field(ge=0.0, le=1.0)
    coverage_gaps:            list[str]  = Field(default_factory=list, description="What this analysis could not address")
    upstream_slots_consumed:  list[str]  = Field(description="output_slot names that were read")

    def to_dict(self) -> dict:
        return self.model_dump()


# ---------------------------------------------------------------------------
# Tier 2 — QualityReport (QualityCheckSkill only)
# ---------------------------------------------------------------------------

class AxisResult(BaseModel):
    """Result for a single quality axis evaluation."""
    model_config = ConfigDict(frozen=True)

    axis:      str
    passed:    bool
    score:     float = Field(ge=0.0, le=1.0)
    reason:    str   = Field(description="One sentence explanation")
    threshold: float = Field(ge=0.0, le=1.0, description="Minimum score required to pass")


class QualityReport(BaseModel):
    """Output contract for QualityCheckSkill."""
    model_config = ConfigDict(frozen=True)

    node_id:                  str
    axes_evaluated:           list[str]
    results:                  dict[str, AxisResult]  # axis_name → AxisResult
    overall_pass:             bool
    overall_score:            float = Field(ge=0.0, le=1.0)
    remediation_suggestion:   str | None = None

    @classmethod
    def from_llm_json(cls, data: dict) -> "QualityReport":
        """Parse the JSON dict produced by the quality_check LLM prompt."""
        axis_results = {
            axis: AxisResult(**result)
            for axis, result in data.get("results", {}).items()
        }
        return cls(
            node_id                = data["node_id"],
            axes_evaluated         = data.get("axes_evaluated", list(axis_results.keys())),
            results                = axis_results,
            overall_pass           = data["overall_pass"],
            overall_score          = float(data.get("overall_score", 0.0)),
            remediation_suggestion = data.get("remediation_suggestion"),
        )

    def to_dict(self) -> dict:
        d = self.model_dump()
        d["results"] = {k: v.model_dump() for k, v in self.results.items()}
        return d


# ---------------------------------------------------------------------------
# Tier 3 — OutputDocument
# ---------------------------------------------------------------------------

OutputFormat = Literal[
    "report", "exec_summary", "explainer",
    "decision_matrix", "bibliography",
    "annotation", "visualization_spec", "knowledge_delta",
]


class OutputDocument(BaseModel):
    """Output contract for all 8 tier 3 output skills."""
    model_config = ConfigDict(frozen=True)

    skill_name:               str
    format:                   OutputFormat
    content:                  str        = Field(description="Final rendered text / structured output")
    audience:                 str
    word_count:               int        = Field(ge=0)
    citations_included:       list[str]  = Field(description="citation_ids present in content")
    coverage_gaps_disclosed:  list[str]  = Field(description="node_ids that were partial or failed")
    disclaimer_present:       bool       = False
    language:                 str        = "en"

    @field_validator("word_count", mode="before")
    @classmethod
    def compute_word_count(cls, v: int, info) -> int:
        # If caller passes 0, auto-compute from content if available
        if v == 0 and "content" in (info.data or {}):
            return len(info.data["content"].split())
        return v

    def to_dict(self) -> dict:
        return self.model_dump()


# ---------------------------------------------------------------------------
# Type alias — what every skill's run() returns to the orchestrator
# ---------------------------------------------------------------------------

# (result_dict, NodeStatus, credibility_float)
# result_dict should be one of: RetrievalOutput.to_dict() | AnalysisOutput.to_dict()
#                              | QualityReport.to_dict()  | OutputDocument.to_dict()
SkillReturn = tuple[dict[str, Any], Any, float]


# ---------------------------------------------------------------------------
# DocumentChunk — from vector_store/schema.py
# ---------------------------------------------------------------------------

@dataclass
class DocumentChunk:
    text: str                          # raw chunk text (≤ 512 tokens)
    source_url: str
    source_title: str
    credibility: float                 # 0–1, from ToolResult.credibility_base
    skill: str                         # retrieval skill that produced this
    query: str                         # the sub-query that found this document
    run_id: str
    chunk_index: int = 0               # position within the parent document
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    embedding: list[float] = field(default_factory=list)

    def to_qdrant_point(self) -> dict[str, Any]:
        """Convert to a qdrant-client PointStruct-compatible dict."""
        return {
            "id": self.id,
            "vector": self.embedding,
            "payload": {
                "run_id":       self.run_id,
                "skill":        self.skill,
                "query":        self.query,
                "source_url":   self.source_url,
                "source_title": self.source_title,
                "credibility":  self.credibility,
                "chunk_index":  self.chunk_index,
                "text":         self.text,
            },
        }

    @classmethod
    def from_qdrant_point(cls, point) -> "DocumentChunk":
        p = point.payload or {}
        vec = getattr(point, "vector", None)
        return cls(
            id=str(point.id),
            text=p.get("text", ""),
            source_url=p.get("source_url", ""),
            source_title=p.get("source_title", "Unknown"),
            credibility=float(p.get("credibility", 0.5)),
            skill=p.get("skill", ""),
            query=p.get("query", ""),
            run_id=p.get("run_id", ""),
            chunk_index=int(p.get("chunk_index", 0)),
            embedding=list(vec) if vec else [],
        )


# ---------------------------------------------------------------------------
# CitationRecord — from citations/registry.py
# ---------------------------------------------------------------------------

@dataclass
class CitationRecord:
    citation_id:       str          # e.g. "[Smith2024]"
    title:             str
    authors:           list[str]
    year:              str | None
    url:               str
    source_type:       str          # matches SourceType literals
    credibility_base:  float
    registered_by:     str          # skill name that found this source
    registered_at_slot: str         # output_slot of the node that registered it
