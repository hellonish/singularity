from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import SearchQuery


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str
    subquestions: list[str]
    tool_names: list[str]
    current_date: str


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    queries: list[SearchQuery]
    source_priority: list[str]
    stopping_criteria: list[str] = Field(min_length=1)

