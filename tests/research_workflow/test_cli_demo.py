import asyncio

from engine.cli.demo import _run_demo
from engine.research_workflow.document import ResearchDocument, validate_document


def test_demo_cli_runs_the_real_graph_and_writes_both_artifacts(tmp_path):
    json_path, markdown_path = asyncio.run(_run_demo("How does the workflow run?", 2, tmp_path))
    document = validate_document(ResearchDocument.model_validate_json(json_path.read_text()))
    assert document.schema_version == "research-document-v1"
    assert markdown_path.read_text().startswith("# Singularity Research CLI Demo")
