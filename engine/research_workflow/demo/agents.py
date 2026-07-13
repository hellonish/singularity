"""Deterministic local collaborators for the demo smoke test.

They exercise the exact graph, cap, QA, writer, and checkpoint path without
requiring a provider key, Modal deployment, or public-network request. Run via
``python -m engine.cli.demo``.
"""
from __future__ import annotations

import hashlib
from typing import Any

from ..dag import ResearchDAG, ResearchNode, ResearchNodeStatus
from ..document import DocumentSection, ParagraphBlock, ReferenceTag, ResearchDocument


class DemoPlanner:
    async def polish_prompt(self, query: str) -> dict[str, Any]:
        return {
            "query": " ".join(query.split()),
            "audience": "practitioner",
            "constraints": ["demo mode uses deterministic local evidence"],
        }

    async def parallel_proposals(self, query: str) -> list[dict[str, Any]]:
        return [
            {"perspective": "coverage", "focus": f"Scope the central question: {query}"},
            {"perspective": "evidence-risk", "focus": "Identify evidence and uncertainty requirements"},
            {"perspective": "narrative", "focus": "Produce a concise cited answer"},
        ]


class DemoLead:
    async def merge(self, query: str, proposals: list[dict[str, Any]], caps) -> ResearchDAG:
        dag = ResearchDAG()
        dag.add_node(
            ResearchNode(
                node_id="n1",
                question=query,
                rationale="Merged from coverage, evidence-risk, and narrative planning perspectives.",
                section_id="answer",
                level=0,
                acceptance_criteria=["Provide a concise answer and disclose demo limitations."],
            ),
            caps,
        )
        return dag


async def demo_resolver(node: ResearchNode, max_tool_calls: int) -> dict[str, Any]:
    source_id = "Demo" + hashlib.sha256(node.question.encode()).hexdigest()[:8]
    return {
        "answered": True,
        "answer_id": f"answer:{node.node_id}",
        "answer": (
            f"Demo execution completed the bounded research node for: {node.question}. "
            "No external web or provider calls were made; use live mode for sourced research."
        ),
        "evidence_ids": [source_id],
        "tool_calls_used": 0,
        "unresolved_gaps": [],
    }


class DemoQA:
    async def review(self, dag: ResearchDAG, caps) -> list[dict[str, Any]]:
        reviews: list[dict[str, Any]] = []
        for section_id in sorted({node.section_id for node in dag.nodes.values()}):
            nodes = [node for node in dag.nodes.values() if node.section_id == section_id]
            passed = all(node.status == ResearchNodeStatus.ANSWERED and node.answer for node in nodes)
            for node in nodes:
                if node.status in {ResearchNodeStatus.ANSWERED, ResearchNodeStatus.QA_FAILED}:
                    node.status = ResearchNodeStatus.PASSED if passed else ResearchNodeStatus.QA_FAILED
            reviews.append({
                "section_id": section_id,
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "gaps": [] if passed else ["missing node answer"],
                "accepted_suggestions": [],
                "rejected_suggestions": [],
            })
        return reviews


class DemoWriter:
    async def write(self, dag: ResearchDAG, query: str, caps=None) -> dict[str, Any]:
        node = next(iter(dag.nodes.values()))
        ref = ReferenceTag(tag=node.evidence_ids[0], name="Demo execution", url="https://example.com")
        document = ResearchDocument(
            title="Singularity Research CLI Demo",
            query=query,
            sections=[DocumentSection(
                section_id=node.section_id,
                title="Answer",
                blocks=[ParagraphBlock(kind="paragraph", text=node.answer or "No answer produced.", reference_ids=[ref.tag])],
            )],
            references=[ref],
            limitations=["Demo mode uses deterministic evidence and does not make external research calls."],
        )
        return document.model_dump(mode="json")
