from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import ClaimEvidence, EvidenceSource


class CitationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str
    source_id: str
    status: Literal["verified", "unsupported", "mismatch", "unreachable"]
    url_exists: bool
    passage_supports_claim: bool
    dates_and_numbers_match: bool
    explanation: str


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mappings: list[ClaimEvidence]
    sources: list[EvidenceSource]


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checks: list[CitationCheck]
    all_verified: bool
    rejected_claims: list[str] = Field(default_factory=list)

