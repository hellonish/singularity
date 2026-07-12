from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import EvidenceItem, EvidenceSource


class EvidenceScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    authority: float = Field(ge=0.0, le=1.0)
    relevance: float = Field(ge=0.0, le=1.0)
    recency: float = Field(ge=0.0, le=1.0)
    directness: float = Field(ge=0.0, le=1.0)
    independence: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    overall: float = Field(ge=0.0, le=1.0)
    rationale: str


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str
    sources: list[EvidenceSource]
    evidence: list[EvidenceItem]


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scores: list[EvidenceScore]
    ranked_source_ids: list[str]

