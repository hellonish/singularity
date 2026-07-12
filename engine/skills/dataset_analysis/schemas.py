from pydantic import BaseModel, ConfigDict, Field


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_request: str
    dataset_name: str
    python_code: str = Field(min_length=1, max_length=20_000)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stdout: str
    findings: list[str]
    warnings: list[str] = Field(default_factory=list)
