"""
Skill I/O Contracts — the single source of truth for every skill's input and output shape.

Rules:
  - All tier 1 skills  → return RetrievalOutput
  - All tier 2 skills  → return AnalysisOutput  (QualityCheckSkill returns QualityReport)
  - All tier 3 skills  → return OutputDocument

If a schema field needs to change, change it here. All skills and tests update accordingly.

Usage in a skill:
    from contracts.skill_contracts import RetrievalOutput, SourceRecord
    ...
    output = RetrievalOutput(sources=[...], query_used=..., ...)
    return output.to_dict(), NodeStatus.OK, credibility
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Source types
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
