from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: Literal["repository", "code", "data", "service", "gpu"]
    objective: str = Field(min_length=1)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str
    findings: str
    warnings: list[str] = Field(default_factory=list)
