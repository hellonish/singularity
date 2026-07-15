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
    # Inline citations are enrichable <cite> chips carrying the exact link.
    assert 'data-host="example.com"' in output
    assert "https://example.com/source" in output
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
    # Inline: one <cite> per host, www stripped, exact URL carried in data-links.
    assert '<cite data-host="arxiv.org"' in output
    assert '<cite data-host="wikipedia.org"' in output
    assert "https://arxiv.org/abs/1234" in output
    assert "https://www.wikipedia.org/wiki/Thing" in output
    # Reference list: one host heading, exact links nested beneath it.
    assert "- **arxiv.org**" in output
    assert "    - [A Paper](https://arxiv.org/abs/1234)" in output
    assert "- **wikipedia.org**" in output
    assert "    - [Encyclopedia](https://www.wikipedia.org/wiki/Thing)" in output


def test_same_host_citations_dedupe_to_one_chip_carrying_every_link():
    """Four GitHub pages cited together render one github.com chip, not four."""
    document = ResearchDocument(
        title="Report",
        query="Question",
        sections=[DocumentSection(section_id="s1", title="Body", blocks=[ParagraphBlock(
            kind="paragraph", text="A claim.", reference_ids=["G1", "G2", "G3", "A1"],
        )])],
        references=[
            ReferenceTag(tag="G1", name="Tree", url="https://github.com/o/r/tree/abc"),
            ReferenceTag(tag="G2", name="README", url="https://github.com/o/r/blob/abc/README.md"),
            ReferenceTag(tag="G3", name="pyproject", url="https://github.com/o/r/blob/abc/pyproject.toml"),
            ReferenceTag(tag="A1", name="Paper", url="https://arxiv.org/abs/1"),
        ],
    )
    output = to_markdown(document)
    # Exactly one github.com chip inline, and one arxiv.org chip.
    assert output.count('data-host="github.com"') == 1
    assert output.count('data-host="arxiv.org"') == 1
    # That single github chip still carries all three exact links.
    for url in ("tree/abc", "README.md", "pyproject.toml"):
        assert url in output
    # Reference list: github.com heading appears once, with three nested links.
    assert output.count("- **github.com**") == 1
    assert output.count("https://github.com/o/r/") >= 3


def test_source_number_tokens_are_stripped_from_prose():
    """Model-leaked ``SOURCE 1`` scaffolding never reaches the reader."""
    document = ResearchDocument(
        title="Report",
        query="Question",
        sections=[DocumentSection(section_id="s1", title="Body", blocks=[ParagraphBlock(
            kind="paragraph",
            text="The API starts on SQLite (SOURCE 1, SOURCE 2) and scales later (SOURCE 3).",
            reference_ids=["A1"],
        )])],
        references=[ReferenceTag(tag="A1", name="Paper", url="https://arxiv.org/abs/1")],
    )
    output = to_markdown(document)
    assert "SOURCE" not in output
    assert "The API starts on SQLite, and scales later." in output


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

