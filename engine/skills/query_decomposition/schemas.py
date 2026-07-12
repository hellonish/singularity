from pydantic import BaseModel, ConfigDict, Field


class Subquestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    question: str
    rationale: str
    depends_on: list[str] = Field(default_factory=list)


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str
    context: str | None = None
    max_subquestions: int = Field(default=8, ge=1, le=20)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str
    subquestions: list[Subquestion]
    scope_notes: list[str] = Field(default_factory=list)

