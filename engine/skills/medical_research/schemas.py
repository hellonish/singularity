from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import ClaimEvidence, EvidenceSource


class MedicalQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    population: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    outcomes: list[str] = Field(default_factory=list)


class MedicalFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding: str
    evidence_level: Literal["high", "moderate", "low", "insufficient"]
    source_ids: list[str]
    limitations: list[str] = Field(default_factory=list)


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    pico: MedicalQuestion | None = None
    date_from: str | None = None
    max_results: int = Field(default=20, ge=1, le=100)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findings: list[MedicalFinding]
    claims: list[ClaimEvidence]
    sources: list[EvidenceSource]
    safety_notes: list[str]
    evidence_gaps: list[str]

