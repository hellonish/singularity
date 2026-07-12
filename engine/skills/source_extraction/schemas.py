from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import EvidenceItem, EvidenceSource


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[EvidenceSource]
    subquestions: list[str]
    max_passages_per_source: int = Field(default=10, ge=1, le=50)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence: list[EvidenceItem]
    extraction_failures: dict[str, str] = Field(default_factory=dict)

