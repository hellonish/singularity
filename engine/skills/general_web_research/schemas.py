from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import EvidenceSource


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    max_results: int = Field(default=8, ge=1, le=20)
    preferred_domains: list[str] = Field(default_factory=list)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer_context: str
    sources: list[EvidenceSource]
    rendered_pages: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
