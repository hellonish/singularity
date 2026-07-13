from engine.research_workflow.document import (
    ChartBlock,
    ChartPoint,
    DocumentSection,
    ReferenceTag,
    ResearchDocument,
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
    assert "[Src1]" in output

