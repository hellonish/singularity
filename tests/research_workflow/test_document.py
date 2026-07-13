import pytest

from engine.research_workflow.document import (
    DocumentSection,
    ParagraphBlock,
    ReferenceTag,
    ResearchDocument,
    StatsBlock,
    StatItem,
    validate_document,
)


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


def test_document_requires_a_reference_for_every_content_block():
    doc = ResearchDocument(
        title="Report",
        query="Question",
        sections=[DocumentSection(section_id="s1", title="Section", blocks=[ParagraphBlock(kind="paragraph", text="x")])],
    )
    with pytest.raises(ValueError, match="must include at least one reference"):
        validate_document(doc)
