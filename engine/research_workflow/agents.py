"""Concrete LLM-backed planner, QA, answer, and writer collaborators."""
from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from _utils.json_parser import extract_object

from .dag import ResearchDAG, ResearchNode, ResearchNodeStatus
from .document import DocumentSection, ParagraphBlock, ReferenceTag, ResearchDocument, validate_document
from engine.llm.groq import ProviderError


# Reasoning tokens share the completion limit with visible JSON. A 500-token
# cap is enough for a direct model but not for models such as DeepSeek R1,
# which may spend the whole allowance thinking before emitting content.
MIN_RESEARCH_COMPLETION_TOKENS = 1_200
MIN_REASONING_RESEARCH_COMPLETION_TOKENS = 6_000


def research_completion_budget(requested: int, model_id: str = "") -> int:
    normalized = model_id.lower()
    is_reasoning_model = any(
        marker in normalized
        for marker in ("gpt-oss", "deepseek-r1", "/r1", "reasoning", "thinking")
    )
    minimum = (
        MIN_REASONING_RESEARCH_COMPLETION_TOKENS
        if is_reasoning_model
        else MIN_RESEARCH_COMPLETION_TOKENS
    )
    return max(minimum, requested)


class TextModel(Protocol):
    async def complete(self, prompt: str, *, max_output_tokens: int) -> str: ...


def _json(text: str) -> dict[str, Any]:
    value = extract_object(text)
    if value is None:
        raise ValueError("model did not return a JSON object")
    return value


class LLMPlanner:
    _PERSPECTIVES = ("coverage", "evidence-risk", "narrative")

    def __init__(self, model: TextModel, *, max_perspectives: int = 3) -> None:
        self.model = model
        self.max_perspectives = max(1, min(max_perspectives, len(self._PERSPECTIVES)))

    async def polish_prompt(self, query: str) -> dict[str, Any]:
        response = await self.model.complete(
            "Return JSON only: {\"query\": string, \"audience\": string, \"constraints\": [string]}. "
            f"Preserve the user's intent while clarifying scope. User query: {query}",
            max_output_tokens=500,
        )
        result = _json(response)
        result.setdefault("query", query)
        result.setdefault("audience", "practitioner")
        result.setdefault("constraints", [])
        return result

    async def parallel_proposals(self, query: str) -> list[dict[str, Any]]:
        async def propose(perspective: str) -> dict[str, Any]:
            response = await self.model.complete(
                "Return JSON only: {\"perspective\": string, \"nodes\": "
                "[{\"question\": string, \"rationale\": string, \"section_id\": string, "
                "\"level\": integer, \"acceptance_criteria\": [string], \"expected_evidence\": [string]}]}. "
                "Produce at most 3 independent nodes with no dependencies. Treat any dates, recency windows, "
                "companies, and topics in the objective as hard constraints; do not replace them with broader or older periods. "
                f"Perspective: {perspective}. Research objective: {query}",
                max_output_tokens=1_200,
            )
            result = _json(response)
            result["perspective"] = perspective
            result.setdefault("nodes", [])
            return result
        return list(await asyncio.gather(*(propose(perspective) for perspective in self._PERSPECTIVES[:self.max_perspectives])))


class DirectResearchPlanner:
    """Zero-completion planner for the cheap, single-question Quick mode."""

    max_perspectives = 0

    async def polish_prompt(self, query: str) -> dict[str, Any]:
        return {
            "query": query,
            "audience": "practitioner",
            "constraints": ["Quick mode preserves the exact user query."],
        }

    async def parallel_proposals(self, query: str) -> list[dict[str, Any]]:
        return [{
            "perspective": "direct",
            "nodes": [{
                "question": query,
                "rationale": "Quick mode researches the user's exact question without LLM planning.",
                "section_id": "answer",
                "level": 0,
                "acceptance_criteria": ["Answer from current, cited evidence."],
                "expected_evidence": ["primary or reputable current sources"],
            }],
        }]


class LLMLead:
    async def merge(self, query: str, proposals: list[dict[str, Any]], caps) -> ResearchDAG:
        dag = ResearchDAG()
        for proposal in proposals:
            for raw in proposal.get("nodes", [])[:3]:
                question = str(raw.get("question", "")).strip()
                if not question:
                    continue
                digest = hashlib.sha256(f"{proposal.get('perspective')}:{question}".encode()).hexdigest()[:10]
                try:
                    dag.add_node(ResearchNode(
                        node_id=f"n_{digest}",
                        question=question,
                        rationale=str(raw.get("rationale", "")),
                        section_id=str(raw.get("section_id", "overview"))[:80] or "overview",
                        level=min(max(int(raw.get("level", 0)), 0), caps.max_dag_depth),
                        acceptance_criteria=[str(item) for item in raw.get("acceptance_criteria", [])][:4],
                        expected_evidence=[str(item) for item in raw.get("expected_evidence", [])][:4],
                    ), caps)
                except (TypeError, ValueError):
                    continue
        if not dag.nodes:
            dag.add_node(ResearchNode(
                node_id="n_root",
                question=query,
                rationale="Fallback root when planner output cannot be used.",
                section_id="overview",
                level=0,
            ), caps)
        return dag


class LLMAnswerer:
    def __init__(self, model: TextModel, caps=None) -> None:
        self.model = model
        # Content budgets come from RunCaps so evidence fan-in, per-source text,
        # and answer length all scale with strength. Defaults match Quick mode
        # so the answerer remains usable without caps (e.g. in unit tests).
        self._max_evidence = getattr(caps, "max_evidence_per_node", 3)
        self._max_source_chars = getattr(caps, "max_source_chars", 12_000)
        self._answer_tokens = getattr(caps, "answer_completion_tokens", 1_200)

    async def __call__(self, node: ResearchNode, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        bounded = evidence[:self._max_evidence]
        excerpts = "\n\n".join(
            f"SOURCE {index + 1}: {item.get('title', '')} | {item.get('url', '')}\n{str(item.get('content', ''))[:self._max_source_chars]}"
            for index, item in enumerate(bounded)
        )
        response = await self.model.complete(
            "Return JSON only: {\"answer\": string, \"unresolved_gaps\": [string]}. "
            "Answer only from the supplied sources; do not invent citations. "
            f"Question: {node.question}\n\nEvidence:\n{excerpts}",
            max_output_tokens=self._answer_tokens,
        )
        result = _json(response)
        result.setdefault("answer", "")
        result.setdefault("unresolved_gaps", [])
        return result


class LLMQA:
    def __init__(self, model: TextModel) -> None:
        self.model = model

    async def review(self, dag: ResearchDAG, caps) -> list[dict[str, Any]]:
        reviews: list[dict[str, Any]] = []
        for section_id in sorted({node.section_id for node in dag.nodes.values()}):
            nodes = [node for node in dag.nodes.values() if node.section_id == section_id]
            payload = [{"node_id": node.node_id, "question": node.question, "answer": node.answer, "gaps": node.unresolved_gaps} for node in nodes]
            response = await self.model.complete(
                "Return JSON only: {\"passed\": boolean, \"score\": number, \"gaps\": [string], "
                "\"suggestions\": [{\"question\": string, \"rationale\": string}]}. "
                "Suggest at most two focused gaps. A section passes only if claims are adequately supported. "
                f"Section: {section_id}\nNodes: {payload}",
                max_output_tokens=900,
            )
            value = _json(response)
            suggestions: list[ResearchNode] = []
            parent = next((node for node in nodes if node.status == ResearchNodeStatus.ANSWERED), None)
            for raw in value.get("suggestions", [])[:caps.max_qa_suggestions_per_section]:
                question = str(raw.get("question", "")).strip()
                if not question or parent is None:
                    continue
                digest = hashlib.sha256(f"{parent.node_id}:{question}".encode()).hexdigest()[:10]
                suggestions.append(ResearchNode(
                    node_id=f"q_{digest}", question=question,
                    rationale=str(raw.get("rationale", "")), section_id=section_id,
                    level=min(parent.level + 1, caps.max_dag_depth), depends_on=[parent.node_id],
                ))
            accepted, rejected = dag.add_suggestions(section_id, suggestions, caps)
            passed = bool(value.get("passed", False)) and not accepted
            for node in nodes:
                if node.status in {ResearchNodeStatus.ANSWERED, ResearchNodeStatus.QA_FAILED}:
                    node.status = ResearchNodeStatus.PASSED if passed else ResearchNodeStatus.QA_FAILED
                    node.unresolved_gaps = list(value.get("gaps", []))
            reviews.append({
                "section_id": section_id,
                "passed": passed,
                "score": float(value.get("score", 0.0)),
                "gaps": list(value.get("gaps", [])),
                "accepted_suggestions": accepted,
                "rejected_suggestions": rejected,
            })
        return reviews


class LLMWriter:
    """Decomposed writer: one outline pass, then one body completion per section.

    Splitting the report into per-section completions gives each section its own
    token budget instead of sharing a single document-wide cap, so total report
    length scales with the section count (which itself grows with strength).
    A single-call path is kept as a fallback for when the outline pass fails.
    """

    def __init__(self, model: TextModel) -> None:
        self.model = model

    async def write(self, dag: ResearchDAG, query: str, caps=None) -> dict[str, Any]:
        section_tokens = getattr(caps, "section_completion_tokens", 2_000)
        max_parallel = getattr(caps, "max_parallel_research_calls", 6)
        nodes = list(dag.nodes.values())
        facts = [
            node.model_dump(include={"node_id", "question", "answer", "source_records", "unresolved_gaps"})
            for node in nodes
        ]

        outline = await self._outline(query, facts)
        if outline is None:
            return await self._write_single_call(dag, query, section_tokens)

        title = str(outline.get("title") or "Research report")[:200]
        plan = [entry for entry in outline.get("sections", []) if isinstance(entry, dict)]
        if not plan:
            return await self._write_single_call(dag, query, section_tokens)

        known_refs = self._known_refs(dag)
        node_by_id = {node.node_id: node for node in nodes}
        semaphore = asyncio.Semaphore(max(1, max_parallel))

        async def write_section(entry: dict[str, Any]) -> DocumentSection | None:
            node_ids = [str(nid) for nid in entry.get("node_ids", []) if str(nid) in node_by_id]
            section_facts = [
                node_by_id[nid].model_dump(include={"question", "answer", "source_records", "unresolved_gaps"})
                for nid in node_ids
            ] or facts
            allowed_tags = sorted({
                str(source["tag"])
                for nid in (node_ids or node_by_id)
                for source in node_by_id[nid].source_records
            })
            async with semaphore:
                return await self._section_body(
                    query=query,
                    section_id=str(entry.get("section_id") or entry.get("id") or "section"),
                    section_title=str(entry.get("title") or "Section"),
                    facts=section_facts,
                    allowed_tags=allowed_tags,
                    max_output_tokens=section_tokens,
                )

        written = await asyncio.gather(*(write_section(entry) for entry in plan))
        sections = [section for section in written if section is not None]
        if not sections:
            return await self._write_single_call(dag, query, section_tokens)

        document = ResearchDocument(
            title=title,
            query=query,
            sections=sections,
            references=[],
            limitations=[str(item) for item in outline.get("limitations", [])][:6],
        )
        self._backfill_references(document, known_refs)
        try:
            return validate_document(document).model_dump(mode="json")
        except ValueError:
            # A section body may cite a tag the outline did not surface, or omit
            # references entirely; fall back to a directly-assembled cited report
            # rather than failing the whole run.
            return _fallback_document(dag, query)

    async def _outline(self, query: str, facts: list[dict[str, Any]]) -> dict[str, Any] | None:
        try:
            response = await self.model.complete(
                "Return JSON only: {\"title\": string, \"limitations\": [string], "
                "\"sections\": [{\"section_id\": string, \"title\": string, \"node_ids\": [string]}]}. "
                "Design a coherent report outline that groups the verified research nodes into ordered sections. "
                "Every section_id must be unique; assign each relevant node_id to exactly one section. "
                f"Research query: {query}\nVerified node records: {facts}",
                max_output_tokens=1_200,
            )
            return _json(response)
        except (ProviderError, TimeoutError, ValueError):
            return None

    async def _section_body(
        self,
        *,
        query: str,
        section_id: str,
        section_title: str,
        facts: list[dict[str, Any]],
        allowed_tags: list[str],
        max_output_tokens: int,
    ) -> DocumentSection | None:
        try:
            response = await self.model.complete(
                "Return JSON only: a single ResearchDocumentV1 section object "
                "{\"section_id\": string, \"title\": string, \"blocks\": [block]}. "
                "Each block is a paragraph, highlight, math, stats, chart, or table with a `kind` field. "
                "Every factual paragraph, stat, chart point, highlight, or math block must reference an existing tag "
                f"from this allowed set: {allowed_tags}. Use at most two stat items per stats block and labels of at most two words. "
                "Write a thorough, well-supported section; do not invent citations or tags outside the allowed set. "
                f"Research query: {query}\nSection id: {section_id}\nSection title: {section_title}\n"
                f"Verified node records for this section: {facts}",
                max_output_tokens=max_output_tokens,
            )
            payload = _json(response)
            payload.setdefault("section_id", section_id)
            payload.setdefault("title", section_title)
            return DocumentSection.model_validate(payload)
        except (ProviderError, TimeoutError, ValueError):
            return None

    async def _write_single_call(self, dag: ResearchDAG, query: str, max_output_tokens: int) -> dict[str, Any]:
        """Original one-shot writer, retained as the outline-failure fallback."""
        facts = [node.model_dump(include={"question", "answer", "source_records", "unresolved_gaps"}) for node in dag.nodes.values()]
        try:
            response = await self.model.complete(
                "Return a JSON ResearchDocumentV1 object only. Use schema_version research-document-v1; include title, query, "
                "sections, references, and limitations. Every section object MUST contain `section_id` (never `id`), `title`, "
                "and `blocks`. Every factual paragraph, stat, chart point, highlight, or math block "
                "must reference an existing tag. Use at most two stat items per stats block and labels of at most two words. "
                f"Research query: {query}\nVerified node records: {facts}",
                max_output_tokens=max(max_output_tokens, 3_000),
            )
            document = ResearchDocument.model_validate(_json(response))
        except (ProviderError, TimeoutError, ValueError):
            return _fallback_document(dag, query)
        self._backfill_references(document, self._known_refs(dag))
        try:
            return validate_document(document).model_dump(mode="json")
        except ValueError:
            return _fallback_document(dag, query)

    @staticmethod
    def _known_refs(dag: ResearchDAG) -> dict[str, dict[str, Any]]:
        known: dict[str, dict[str, Any]] = {}
        for node in dag.nodes.values():
            for source in node.source_records:
                known[str(source["tag"])] = source
        return known

    @staticmethod
    def _backfill_references(document: ResearchDocument, known_refs: dict[str, dict[str, Any]]) -> None:
        existing = {reference.tag for reference in document.references}
        for tag, source in known_refs.items():
            if tag not in existing:
                document.references.append(ReferenceTag(
                    tag=tag,
                    name=source["name"],
                    title=source["title"],
                    url=source["url"],
                    source_type=source["source_type"],
                    date=source.get("date"),
                ))


def _fallback_document(dag: ResearchDAG, query: str) -> dict[str, Any]:
    """Produce a cited report when the optional writer completion fails."""
    references: dict[str, ReferenceTag] = {}
    sections: list[DocumentSection] = []
    for node in dag.nodes.values():
        tags: list[str] = []
        for source in node.source_records:
            tag = str(source.get("tag", ""))
            url = str(source.get("url", ""))
            if not tag or not url.startswith(("https://", "http://")):
                continue
            tags.append(tag)
            references.setdefault(tag, ReferenceTag(
                tag=tag,
                name=str(source.get("name") or url)[:120],
                title=str(source.get("title") or ""),
                url=url,
                source_type=str(source.get("source_type") or "web"),
                date=source.get("date"),
            ))
        if node.answer and tags:
            sections.append(DocumentSection(
                section_id=node.node_id,
                title=node.question[:160],
                blocks=[ParagraphBlock(kind="paragraph", text=node.answer, reference_ids=tags)],
            ))
    document = ResearchDocument(
        title="Research report (fallback assembly)",
        query=query,
        sections=sections,
        references=list(references.values()),
        limitations=["The writer model failed, so this report was assembled directly from completed cited research nodes."],
    )
    return validate_document(document).model_dump(mode="json")
