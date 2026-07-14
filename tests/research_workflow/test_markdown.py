from engine.research_workflow.document import (
    ChartBlock,
    ChartPoint,
    DocumentSection,
    ParagraphBlock,
    ReferenceTag,
    ResearchDocument,
    validate_document,
)
from engine.research_workflow.markdown import to_markdown


def test_chart_export_degrades_to_a_cited_markdown_table():
    document = ResearchDocument(
        title="Report",
        query="Question",
        sections=[DocumentSection(section_id="s1", title="Data", blocks=[ChartBlock(
            kind="chart",
            chart_type="bar",
            title="Values",
            unit="%",
            points=[ChartPoint(label="A", value=4.2, reference_ids=["Src1"])],
        )])],
        references=[ReferenceTag(tag="Src1", name="Source", url="https://example.com/source")],
    )
    output = to_markdown(document)
    assert "| Label | Value |" in output
    # Inline citations are hyperlinked and labelled with the website name.
    assert "[example.com](https://example.com/source)" in output
    assert "[Src1]" not in output


def test_inline_and_listed_references_show_the_bare_website_name():
    document = ResearchDocument(
        title="Report",
        query="Question",
        sections=[DocumentSection(section_id="s1", title="Body", blocks=[ParagraphBlock(
            kind="paragraph", text="A claim.", reference_ids=["A1", "W1"],
        )])],
        references=[
            ReferenceTag(tag="A1", name="A Paper", url="https://arxiv.org/abs/1234"),
            ReferenceTag(tag="W1", name="Encyclopedia", url="https://www.wikipedia.org/wiki/Thing"),
        ],
    )
    output = to_markdown(document)
    # Inline: hyperlinked, labelled by domain, and www stripped.
    assert "[arxiv.org](https://arxiv.org/abs/1234)" in output
    assert "[wikipedia.org](https://www.wikipedia.org/wiki/Thing)" in output
    # Reference list: bold label is the website name, not the opaque tag.
    assert "- **arxiv.org** [A Paper](https://arxiv.org/abs/1234)" in output
    assert "- **wikipedia.org** [Encyclopedia](https://www.wikipedia.org/wiki/Thing)" in output


def _para(text: str) -> ParagraphBlock:
    return ParagraphBlock(kind="paragraph", text=text, reference_ids=["Src1"])


def test_nested_subsections_render_as_deepening_headings():
    """Section -> Subsection -> Subsubsection maps to ## -> ### -> ####."""
    document = ResearchDocument(
        title="Report",
        query="Question",
        sections=[DocumentSection(
            section_id="s1",
            title="Top",
            blocks=[_para("intro")],
            children=[DocumentSection(
                section_id="s1a",
                title="Sub",
                blocks=[_para("body")],
                children=[DocumentSection(
                    section_id="s1a1",
                    title="SubSub",
                    blocks=[_para("deep")],
                )],
            )],
        )],
        references=[ReferenceTag(tag="Src1", name="Source", url="https://example.com/source")],
    )
    # Nested children must pass the recursive reference validator.
    validate_document(document)
    output = to_markdown(document)
    assert "## Top" in output
    assert "### Sub" in output
    assert "#### SubSub" in output

