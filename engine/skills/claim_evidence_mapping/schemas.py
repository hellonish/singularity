from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import ClaimEvidence, EvidenceItem


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[str]
    evidence: list[EvidenceItem]


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mappings: list[ClaimEvidence]
    unsupported_claims: list[str] = Field(default_factory=list)

