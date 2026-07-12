from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import ClaimEvidence


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str
    claims: list[ClaimEvidence]
    contradictions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    max_characters: int = Field(default=12000, ge=1000)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    compressed_context: str
    retained_source_ids: list[str]
    uncertainties: list[str]
    open_questions: list[str]

