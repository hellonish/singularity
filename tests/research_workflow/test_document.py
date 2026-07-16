import pytest

from engine.research_workflow.document import (
    DocumentSection,
    HighlightBlock,
    ParagraphBlock,
    ReferenceTag,
    ResearchDocument,
    StatsBlock,
    StatItem,
    validate_document,
)


def test_blocks_tolerate_common_writer_key_deviations():
    """Writer models emit content/tag/tags/stats and bare-int stat values; the
    schema must coerce these rather than drop the whole section."""
    para = ParagraphBlock.model_validate({"kind": "paragraph", "content": "hi", "tag": "S1"})
    assert para.text == "hi"
    assert para.reference_ids == ["S1"]  # single string wrapped to a list

    highlight = HighlightBlock.model_validate({"kind": "highlight", "text": "body", "tags": ["S2"]})
    assert highlight.body == "body"
    assert highlight.title == "Highlight"  # default when omitted
    assert highlight.reference_ids == ["S2"]

    stats = StatsBlock.model_validate(
        {"kind": "stats", "stats": [{"label": "Growth", "value": 4, "tag": "S3"}]}
    )
    assert stats.items[0].value == "4"  # int coerced to string
    assert stats.items[0].reference_ids == ["S3"]


def test_canonical_block_field_names_still_validate():
    para = ParagraphBlock.model_validate(
        {"kind": "paragraph", "text": "x", "reference_ids": ["S9"]}
    )
    assert para.text == "x"
    assert para.reference_ids == ["S9"]


def test_document_section_accepts_model_id_alias_and_normalizes_it():
    document = ResearchDocument.model_validate({
        "title": "Alias test",
        "query": "test",
        "sections": [{
            "id": "overview",
            "title": "Overview",
            "blocks": [{"kind": "paragraph", "text": "Supported.", "reference_ids": ["S123"]}],
        }],
        "references": [{"tag": "S123", "name": "Source", "url": "https://example.test"}],
    })

    assert document.sections[0].section_id == "overview"
    assert "section_id" in document.model_dump()["sections"][0]


def test_document_validates_linked_references_and_stat_limit():
    doc = ResearchDocument(
        title="Report",
        query="Question",
        sections=[
            DocumentSection(
                section_id="s1",
                title="Section",
                blocks=[
                    ParagraphBlock(kind="paragraph", text="Finding", reference_ids=["Src1"]),
                    StatsBlock(kind="stats", items=[StatItem(label="Risk", value="4.2", reference_ids=["Src1"])]),
                ],
            )
        ],
        references=[ReferenceTag(tag="Src1", name="Source", url="https://example.com/source")],
    )
    assert validate_document(doc) == doc


def test_document_rejects_unknown_reference():
    doc = ResearchDocument(
        title="Report",
        query="Question",
        sections=[DocumentSection(section_id="s1", title="Section", blocks=[ParagraphBlock(kind="paragraph", text="x", reference_ids=["Missing"])])],
    )
    with pytest.raises(ValueError, match="unknown references"):
        validate_document(doc)


def test_document_rejects_a_section_with_no_content():
    """A heading with neither blocks nor children renders as an empty shell."""
    doc = ResearchDocument(
        title="Report",
        query="Question",
        sections=[DocumentSection(section_id="s1", title="Hollow")],
    )
    with pytest.raises(ValueError, match="has no content"):
        validate_document(doc)


def test_document_accepts_a_container_section_whose_children_hold_the_content():
    doc = ResearchDocument(
        title="Report",
        query="Question",
        sections=[DocumentSection(
            section_id="s1",
            title="Container",
            children=[DocumentSection(
                section_id="s1-a",
                title="Child",
                blocks=[ParagraphBlock(kind="paragraph", text="Finding", reference_ids=["Src1"])],
            )],
        )],
        references=[ReferenceTag(tag="Src1", name="Source", url="https://example.com/source")],
    )
    assert validate_document(doc) == doc


def test_document_requires_a_reference_for_every_content_block():
    doc = ResearchDocument(
        title="Report",
        query="Question",
        sections=[DocumentSection(section_id="s1", title="Section", blocks=[ParagraphBlock(kind="paragraph", text="x")])],
    )
    with pytest.raises(ValueError, match="must include at least one reference"):
        validate_document(doc)


def test_validate_document_rejects_a_report_with_no_sections():
    doc = ResearchDocument(
        title="Research report",
        query="What changed?",
        sections=[],
        references=[],
    )

    with pytest.raises(ValueError, match="at least one cited section"):
        validate_document(doc)
