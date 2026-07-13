"""Standalone deterministic smoke test for the bounded research workflow.

Runs the exact LangGraph research graph with local demo collaborators (no
provider key, Modal deployment, or network request) and writes both the JSON
document and the rendered Markdown report. Use it to verify graph, cap, QA,
writer, and checkpoint wiring end to end.

    python -m engine.cli.demo "How does the workflow run?" --strength 2
"""
from __future__ import annotations

import argparse
import asyncio
import uuid
from pathlib import Path

from engine.research_workflow.caps import RunCaps
from engine.research_workflow.demo import (
    DemoLead,
    DemoPlanner,
    DemoQA,
    DemoWriter,
    demo_resolver,
)
from engine.research_workflow.document import ResearchDocument, validate_document
from engine.research_workflow.markdown import to_markdown
from engine.research_workflow.workflow import ResearchWorkflow


async def _run_demo(query: str, strength: int, output_dir: Path) -> tuple[Path, Path]:
    workflow = ResearchWorkflow(
        planner=DemoPlanner(),
        lead=DemoLead(),
        resolver=demo_resolver,
        qa_reviewer=DemoQA(),
        writer=DemoWriter(),
    )
    state = await workflow.run(run_id=uuid.uuid4().hex, query=query, caps=RunCaps.for_strength(strength))
    document = validate_document(ResearchDocument.model_validate(state["report"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "research-document.json"
    markdown_path = output_dir / "research-report.md"
    json_path.write_text(document.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(to_markdown(document), encoding="utf-8")
    return json_path, markdown_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Singularity bounded research workflow — deterministic demo")
    parser.add_argument("query", help="Research question")
    parser.add_argument("--strength", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--output-dir", type=Path, default=Path(".artifacts/research"))
    args = parser.parse_args()
    json_path, markdown_path = asyncio.run(_run_demo(args.query, args.strength, args.output_dir))
    print(f"Demo research workflow completed.\nJSON: {json_path}\nMarkdown: {markdown_path}")


if __name__ == "__main__":
    main()
