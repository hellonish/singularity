from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import EvidenceItem, EvidenceSource


class DuplicateGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical_source_id: str
    duplicate_source_ids: list[str]
    reason: str


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[EvidenceSource]
    evidence: list[EvidenceItem]


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[EvidenceSource]
    evidence: list[EvidenceItem]
    duplicate_groups: list[DuplicateGroup] = Field(default_factory=list)

