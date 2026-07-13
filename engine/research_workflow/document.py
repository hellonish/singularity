from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class ReferenceTag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tag: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{1,31}$")
    name: str = Field(min_length=1, max_length=120)
    title: str = ""
    url: str = Field(pattern=r"^https?://")
    source_type: str = "web"
    date: str | None = None


class ParagraphBlock(BaseModel):
    kind: Literal["paragraph"]
    text: str
    reference_ids: list[str] = Field(default_factory=list)


class HighlightBlock(BaseModel):
    kind: Literal["highlight"]
    title: str
    body: str
    reference_ids: list[str] = Field(default_factory=list)


class MathBlock(BaseModel):
    kind: Literal["math"]
    latex: str = Field(min_length=1)
    display: bool = True
    reference_ids: list[str] = Field(default_factory=list)


class StatItem(BaseModel):
    label: str = Field(min_length=1, max_length=64)
    value: str
    reference_ids: list[str] = Field(default_factory=list)

    @field_validator("label")
    @classmethod
    def max_two_words(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value.split()) > 2:
            raise ValueError("stat labels may contain at most two words")
        return value


class StatsBlock(BaseModel):
    kind: Literal["stats"]
    items: list[StatItem] = Field(min_length=1, max_length=2)


class ChartPoint(BaseModel):
    label: str
    value: float
    reference_ids: list[str] = Field(default_factory=list)


class ChartBlock(BaseModel):
    kind: Literal["chart"]
    chart_type: Literal["bar", "pie", "line", "area", "scatter"]
    title: str
    unit: str = ""
    points: list[ChartPoint] = Field(min_length=1)


class TableBlock(BaseModel):
    kind: Literal["table"]
    columns: list[str] = Field(min_length=1)
    rows: list[list[str]] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)


DocumentBlock = Annotated[
    ParagraphBlock | HighlightBlock | MathBlock | StatsBlock | ChartBlock | TableBlock,
    Field(discriminator="kind"),
]


class DocumentSection(BaseModel):
    # Models commonly emit a generic `id` key even when asked for
    # `section_id`. Accept it only at this boundary, then serialize the
    # canonical field name everywhere else.
    section_id: str = Field(validation_alias=AliasChoices("section_id", "id"))
    title: str
    blocks: list[DocumentBlock] = Field(default_factory=list)
    children: list["DocumentSection"] = Field(default_factory=list)


class ResearchDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["research-document-v1"] = "research-document-v1"
    title: str
    query: str
    sections: list[DocumentSection]
    references: list[ReferenceTag] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


DocumentSection.model_rebuild()


def validate_document(document: ResearchDocument) -> ResearchDocument:
    refs = {ref.tag for ref in document.references}
    for section in _sections(document.sections):
        for block in section.blocks:
            ids = _reference_ids(block)
            if not ids:
                raise ValueError(f"block in {section.section_id} must include at least one reference")
            if isinstance(block, StatsBlock) and any(not item.reference_ids for item in block.items):
                raise ValueError(f"every stat item in {section.section_id} must include a reference")
            if isinstance(block, ChartBlock) and any(not point.reference_ids for point in block.points):
                raise ValueError(f"every chart point in {section.section_id} must include a reference")
            missing = set(ids) - refs
            if missing:
                raise ValueError(f"block in {section.section_id} has unknown references: {sorted(missing)}")
            if isinstance(block, ChartBlock) and not block.points:
                raise ValueError("charts require at least one point")
    return document


def _sections(sections: list[DocumentSection]):
    for section in sections:
        yield section
        yield from _sections(section.children)


def _reference_ids(block: DocumentBlock) -> list[str]:
    if isinstance(block, StatsBlock):
        return [ref for item in block.items for ref in item.reference_ids]
    if isinstance(block, ChartBlock):
        return [ref for point in block.points for ref in point.reference_ids]
    return list(getattr(block, "reference_ids", []))
