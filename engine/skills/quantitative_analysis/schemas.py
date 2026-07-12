from pydantic import BaseModel, ConfigDict, Field


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expression: str
    precision: int = Field(default=6, ge=0, le=12)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expression: str
    result: str
    explanation: str
