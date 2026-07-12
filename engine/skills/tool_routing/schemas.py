from pydantic import BaseModel, ConfigDict, Field


class ToolRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subquestion_id: str
    tool_names: list[str]
    rationale: str
    fallback_tools: list[str] = Field(default_factory=list)


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subquestions: list[str]
    available_tools: list[str]


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    routes: list[ToolRoute]
    unroutable: list[str] = Field(default_factory=list)

