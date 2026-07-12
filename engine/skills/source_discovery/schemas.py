from pydantic import BaseModel, ConfigDict, Field

from engine.skills.models import EvidenceSource, SearchQuery


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    queries: list[SearchQuery]
    tool_names: list[str]
    max_results_per_query: int = Field(default=10, ge=1, le=100)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sources: list[EvidenceSource]
    queries_executed: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)

