from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_type: Literal["chat", "report"]
    resource_id: str
    query: str
    limit: int = Field(default=8, ge=1, le=20)


class SkillOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunks: list[str]
    document_ids: list[str]
    source_urls: list[str]
