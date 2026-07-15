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


# Writer models routinely emit reasonable-but-wrong key names for block fields
# (``content`` for a paragraph's ``text``, ``tag``/``tags`` for
# ``reference_ids``, ``stats`` for a stats block's ``items``). Accepting those
# aliases keeps one stray key from dropping an entire section. ``populate_by_name``
# keeps the canonical field names working alongside the aliases.
_BLOCK_CONFIG = ConfigDict(populate_by_name=True)

# Common alias spellings for the citation list, shared by every block type.
_REFERENCE_IDS_ALIASES = AliasChoices("reference_ids", "reference_id", "tags", "tag", "refs", "ref")


class _CitedModel(BaseModel):
    """Base for every model carrying ``reference_ids``: shared config + coercion."""

    model_config = _BLOCK_CONFIG
    reference_ids: list[str] = Field(default_factory=list, validation_alias=_REFERENCE_IDS_ALIASES)

    @field_validator("reference_ids", mode="before")
    @classmethod
    def _wrap_single_reference(cls, value: object) -> object:
        # A model may cite a single source as a bare string ("tag": "S123") where
        # the schema expects a list; wrap it so the section survives.
        if isinstance(value, str):
            return [value]
        return value


class ParagraphBlock(_CitedModel):
    kind: Literal["paragraph"]
    text: str = Field(validation_alias=AliasChoices("text", "content", "body"))


class HighlightBlock(_CitedModel):
    kind: Literal["highlight"]
    title: str = Field(default="Highlight", validation_alias=AliasChoices("title", "heading", "label"))
    body: str = Field(validation_alias=AliasChoices("body", "text", "content"))


class MathBlock(_CitedModel):
    kind: Literal["math"]
    latex: str = Field(min_length=1)
    display: bool = True


class StatItem(_CitedModel):
    label: str = Field(min_length=1, max_length=64)
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_to_string(cls, value: object) -> object:
        # Models frequently emit a bare number for a stat value; the schema is a
        # string so a "4" and a "4%" render identically. Coerce rather than reject.
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return format(value, "g") if isinstance(value, float) else str(value)
        return value

    @field_validator("label")
    @classmethod
    def max_two_words(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value.split()) > 2:
            raise ValueError("stat labels may contain at most two words")
        return value


class StatsBlock(BaseModel):
    model_config = _BLOCK_CONFIG
    kind: Literal["stats"]
    items: list[StatItem] = Field(
        min_length=1, max_length=2, validation_alias=AliasChoices("items", "stats", "values")
    )


class ChartPoint(_CitedModel):
    label: str
    value: float


class ChartBlock(BaseModel):
    model_config = _BLOCK_CONFIG
    kind: Literal["chart"]
    chart_type: Literal["bar", "pie", "line", "area", "scatter"]
    title: str
    unit: str = ""
    points: list[ChartPoint] = Field(min_length=1, validation_alias=AliasChoices("points", "data"))


class TableBlock(_CitedModel):
    kind: Literal["table"]
    columns: list[str] = Field(min_length=1)
    rows: list[list[str]] = Field(default_factory=list)


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
        # A heading with neither blocks nor subsections renders as an empty
        # shell; rejecting it here routes the writer to its fallback instead
        # of shipping a hollow report.
        if not section.blocks and not section.children:
            raise ValueError(f"section {section.section_id} has no content")
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
