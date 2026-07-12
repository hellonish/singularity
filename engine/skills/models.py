"""Shared contracts for declarative research skills."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillConfig(BaseModel):
    """Validated contents of one skill's ``config.yaml``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    version: str
    kind: Literal["core", "domain"]
    description: str = Field(min_length=1)
    tools: tuple[str, ...] = ()
    instructions: str = "instructions.md"
    schemas: str = "schemas.py"

    @field_validator("tools")
    @classmethod
    def tools_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("tools must not contain duplicates")
        return value


@dataclass(frozen=True)
class SkillDefinition:
    """A loaded skill and the contracts required to invoke it."""

    config: SkillConfig
    root: Path
    instructions: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    @property
    def id(self) -> str:
        return self.config.id


class EvidenceSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    title: str
    url: str
    source_type: str
    date: str | None = None
    authority: float = Field(ge=0.0, le=1.0)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    passage: str
    relevance: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, object] = Field(default_factory=dict)


class ClaimEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    source_ids: list[str]
    supporting_passage: str
    confidence: float = Field(ge=0.0, le=1.0)


class SearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    purpose: str
    preferred_sources: list[str] = Field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None

