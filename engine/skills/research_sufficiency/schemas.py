from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import ClaimEvidence, SearchQuery


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subquestions: list[str]
    stopping_criteria: list[str]
    mappings: list[ClaimEvidence]
    unresolved_contradictions: list[str] = Field(default_factory=list)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sufficient: bool
    coverage_score: float = Field(ge=0.0, le=1.0)
    covered_subquestions: list[str]
    gaps: list[str]
    next_queries: list[SearchQuery] = Field(default_factory=list)

