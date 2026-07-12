from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import ClaimEvidence


class Contradiction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_a: str
    claim_b: str
    source_ids: list[str]
    explanation: str
    resolution: Literal["resolved", "unresolved", "not_a_contradiction"]


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ClaimEvidence]


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contradictions: list[Contradiction]
    unresolved_questions: list[str] = Field(default_factory=list)

