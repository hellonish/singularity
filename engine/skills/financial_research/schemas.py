from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import ClaimEvidence, EvidenceSource


class FinancialMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    value: float | None = None
    unit: str
    period: str
    change_percent: float | None = None
    source_id: str


class FinancialRisk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Literal["demand", "competition", "supply", "regulatory", "financial", "other"]
    description: str
    source_ids: list[str]


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: str
    question: str
    periods: list[str] = Field(default_factory=list)
    max_results: int = Field(default=20, ge=1, le=100)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metrics: list[FinancialMetric]
    claims: list[ClaimEvidence]
    risks: list[FinancialRisk]
    sources: list[EvidenceSource]
    uncertainties: list[str]

