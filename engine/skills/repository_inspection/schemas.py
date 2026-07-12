from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository_url: str
    ref: str | None = None
    operations: list[Literal["files", "git_summary", "tests", "static_analysis"]] = Field(default_factory=lambda: ["files"])


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findings: str
    operations_completed: list[str]
    warnings: list[str] = Field(default_factory=list)
