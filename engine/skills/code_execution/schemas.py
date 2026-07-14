from pydantic import BaseModel, ConfigDict, Field


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str
    files: dict[str, str] = Field(min_length=1, max_length=20)
    command: list[str] = Field(min_length=1, max_length=20)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stdout: str
    stderr: str = ""
    exit_code: int
    verified: bool
