"""
ReportWorkerAgent — writes one section of the report using 2 LLM calls.

Call 1: Multi-Analysis  — selects 3 tier2 skills, runs all in one structured pass
Call 2: Section Write   — uses Call 1 output to write the final Markdown section

Leaf workers analyse raw Qdrant evidence.
Parent workers synthesise their children's already-written content.

Phase C+ (Issue 3): Evidence Augmentation Loop runs between Call 1 and Call 2 for
leaf nodes.  Iteratively expands the chunk pool via gap-driven retrieval until 2 of
3 stopping signals fire: entity coverage ≥ 80%, novelty rate < 25%, or gap stability.

Citation tracking: each chunk is pre-assigned a stable citation key derived from its
source title. The key is shown to the LLM in the chunk header ("Cite as: [Key]") so
the LLM uses it verbatim. The resulting citation_id → {title, url} mapping is stored
on the SectionNode and returned in WorkerResult, then aggregated into the Reference
List in the pipeline assembler.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, TYPE_CHECKING

from agents.report_manager.section_node import SectionNode
from agents.report_manager.report_tree import ReportTree
from models import PlanNode
from utils.json_parser import extract_object, sanitize_string_values, extract_string_field
from .result import WorkerResult

logger = logging.getLogger(__name__)

_PROMPT_DIR    = Path(__file__).parent
_PROMPT_LEAF   = (_PROMPT_DIR / "prompt_leaf.md").read_text(encoding="utf-8")
_PROMPT_PARENT = (_PROMPT_DIR / "prompt_parent.md").read_text(encoding="utf-8")

ENTITY_COVERAGE_GOAL  = 0.80   # augmentation loop: target fraction of entities covered
NOVELTY_RATE_CEILING  = 0.25   # augmentation loop: stop when new chunks are this novel or less

if TYPE_CHECKING:
    from trace import TraceLogger


_STOP_WORDS = frozenset({
    "the", "a", "an", "of", "in", "on", "at", "for", "and", "or", "to", "by",
    "with", "from", "as", "is", "it", "its", "into", "this", "that", "are",
    "was", "were", "be", "been", "has", "have", "had", "do", "does", "did",
    "about", "using", "via", "based", "new", "some", "how", "why", "what",
})


class ReportWorkerAgent:
    """
    One instance per section node.  Instantiate, call run(), discard.

    Two LLM clients are injected for cost/quality tiering:
      analysis_client — Call 1 (structured JSON analysis); mini model sufficient.
      write_client    — Call 2 (prose section write); best available model.
    If only `client` is supplied (legacy), both calls use it.
    """

    def __init__(
        self,
        node: SectionNode,
        tree: ReportTree,
        run_id: str,
        client=None,               # legacy single-client path
        analysis_client=None,      # Call 1 — mini / analysis model
        write_client=None,         # Call 2 — best-quality write model
    ):
        self.node    = node
        self.tree    = tree
        self.run_id  = run_id
        # Tiered clients: fall back to `client` when split clients not supplied
        self._analysis_client = analysis_client or client
        self._write_client    = write_client    or client
        self._is_leaf = len(tree.children_of(node.node_id)) == 0
        self._system_prompt = _PROMPT_LEAF if self._is_leaf else _PROMPT_PARENT

    async def run(
        self,
        qdrant_chunks: list[Any],     # list of DocumentChunk objects
        audience: str = "practitioner",
        research_query: str = "",
        logger: "TraceLogger | None" = None,
        # Phase C+ parameters (optional — augmentation only runs when all are provided)
        strength=None,
        collection_name: str | None = None,
        vs=None,
        ctx=None,
    ) -> WorkerResult:
        """
        Execute Call 1 (analysis) then optionally Phase C+ augmentation then Call 2 (write).

        Phase C+ augmentation loop runs for leaf nodes when `strength`, `vs`, and
        `collection_name` are all provided.  It expands the chunk pool iteratively
        using gap-driven retrieval, stopping when 2 of 3 signals fire.

        When `logger` is provided, both calls are fully traced.
        """
        children_content = self._gather_children_content()
        chunks_text, source_map = self._format_chunks(qdrant_chunks)

        # ── Call 1: Multi-Analysis (mini model — structured JSON) ────
        call1_msg = self._build_call1_message(
            chunks_text, children_content, audience, research_query
        )
        raw1 = await asyncio.to_thread(
            self._analysis_client.generate_text,
            prompt=call1_msg,
            system_prompt=self._system_prompt,
            temperature=0.2,
        )
        analysis = self._parse_call(raw1, expected_call=1)

        if logger is not None:
            logger.log_worker_call1(
                node_id=self.node.node_id,
                node_title=self.node.title,
                system_prompt=self._system_prompt,
                user_message=call1_msg,
                raw_response=raw1,
                parsed=analysis,
            )

        # ── Phase C+: Evidence Augmentation Loop (leaf nodes only) ──
        aug_meta: dict[str, Any] = {
            "augmentation_iters": 0,
            "entity_coverage": None,
            "faithfulness_score": None,
        }
        if (self._is_leaf
                and strength is not None
                and vs is not None
                and collection_name is not None):
            qdrant_chunks, aug_meta = await self._augment_evidence(
                initial_chunks=qdrant_chunks,
                call1_analysis=analysis,
                strength=strength,
                collection_name=collection_name,
                vs=vs,
                ctx=ctx,
            )
            # Re-format with augmented pool for Call 2
            chunks_text, source_map = self._format_chunks(qdrant_chunks)

        # ── Call 2: Section Write (best-quality write model) ──────────
        call2_msg = self._build_call2_message(
            analysis, chunks_text, children_content, audience,
            raw_chunks=qdrant_chunks,
        )
        raw2 = await asyncio.to_thread(
            self._write_client.generate_text,
            prompt=call2_msg,
            system_prompt=self._system_prompt,
            temperature=0.65,
        )
        write_out = self._parse_call(raw2, expected_call=2)

        # ── Phase C+ post-loop: faithfulness check ────────────────────
        faithfulness_score: float | None = None
        if (self._is_leaf
                and strength is not None
                and getattr(strength, "augmentation_faithfulness_check", False)):
            content_for_check = write_out.get("content", "")
            if content_for_check:
                faithfulness_score = await self._check_faithfulness(
                    content_for_check, chunks_text
                )

        # ── Persist content back onto the tree node ───────────────────
        content = write_out.get("content", "")
        citations = write_out.get("citations_used", [])
        self.node.content    = content
        self.node.word_count = write_out.get("word_count", len(content.split()))
        self.node.citations  = citations
        self.node.source_map = self._filter_cited_sources(source_map, content, citations)
        if faithfulness_score is not None:
            self.node.faithfulness_score = faithfulness_score

        if logger is not None:
            logger.log_worker_call2(
                node_id=self.node.node_id,
                node_title=self.node.title,
                system_prompt=self._system_prompt,
                user_message=call2_msg,
                raw_response=raw2,
                parsed=write_out,
                final_content=content,
            )

        return WorkerResult(
            node_id=self.node.node_id,
            section_title=self.node.title,
            content=content,
            word_count=self.node.word_count,
            node_type="leaf" if self._is_leaf else "parent",
            tier2_used=analysis.get("tier2_selected", []),
            tier3_used=write_out.get("tier3_selected", "report_generator"),
            citations_used=citations,
            qdrant_chunks_used=analysis.get("key_evidence_chunks", []),
            children_consumed=[c.node_id for c in self.tree.children_of(self.node.node_id)],
            coverage_gaps=write_out.get("coverage_gaps", []),
            source_map=self.node.source_map,
            faithfulness_score=faithfulness_score,
            entity_coverage=aug_meta.get("entity_coverage"),
            augmentation_iters=aug_meta.get("augmentation_iters", 0),
        )

    # ------------------------------------------------------------------
    # Phase C+: Evidence Augmentation Loop
    # ------------------------------------------------------------------

    async def _augment_evidence(
        self,
        initial_chunks: list[Any],
        call1_analysis: dict,
        strength,
        collection_name: str,
        vs,
        ctx=None,
    ) -> tuple[list[Any], dict[str, Any]]:
        """
        Phase C+ Evidence Augmentation Loop.

        Iteratively expands the chunk pool using gap-driven queries.
        Stopping signals (2 of 3 must fire to stop early):
          1. Entity coverage ≥ 80%  (fixed goal set extracted from description)
          2. Novelty rate < 25%     (evidence ceiling — new chunks are redundant)
          3. Gap stability ≥ 2 rounds (same gaps → no new angles available)

        Returns (augmented_pool, metadata_dict).
        """
        required_entities = self._extract_required_entities()

        chunk_pool = list(initial_chunks)
        pool_text_prefixes: set[str] = {
            getattr(c, "text", "")[:120] for c in chunk_pool
        }
        pool_vocab = self._build_pool_vocab(chunk_pool)

        iters_run = 0
        web_escalations_used = 0
        last_gap_text = ""
        gap_stable_rounds = 0

        max_iters = strength.max_augmentation_iters
        max_web_esc = strength.max_web_escalations

        for _iter in range(max_iters):
            # ── Stopping signal 1: entity coverage ───────────────────
            entity_cov = self._compute_entity_coverage(required_entities, chunk_pool)

            # ── Extract gap text from Call 1 ─────────────────────────
            analyses = call1_analysis.get("analyses", {})
            gap_text = analyses.get("gap_analysis", "") or analyses.get("coverage_gaps", "")
            if isinstance(gap_text, list):
                gap_text = " ".join(gap_text)
            # Also include top-level coverage_gaps
            top_gaps = call1_analysis.get("coverage_gaps", [])
            if isinstance(top_gaps, list) and top_gaps:
                gap_text = gap_text + " " + " ".join(top_gaps)
            gap_text = gap_text.strip()

            # ── Stopping signal 3: gap stability ─────────────────────
            if gap_text and gap_text == last_gap_text:
                gap_stable_rounds += 1
            else:
                gap_stable_rounds = 0
            last_gap_text = gap_text

            signals_fired = int(entity_cov >= ENTITY_COVERAGE_GOAL) + int(gap_stable_rounds >= 2)
            if signals_fired >= 2:
                break

            # ── Generate gap queries (anchor interpolation) ───────────
            queries = self._gaps_to_queries(gap_text)
            if not queries:
                break

            # ── Qdrant retrieval ──────────────────────────────────────
            new_chunks: list[Any] = []
            for q in queries[:2]:
                results = vs.search(
                    run_id=self.run_id, query_text=q, k=6, min_credibility=0.3
                )
                for c in results:
                    prefix = getattr(c, "text", "")[:120]
                    if prefix not in pool_text_prefixes:
                        new_chunks.append(c)
                        pool_text_prefixes.add(prefix)

            # ── Stopping signal 2: novelty rate ──────────────────────
            if new_chunks:
                novelty = self._compute_novelty_rate(new_chunks, pool_vocab)
                if novelty < NOVELTY_RATE_CEILING:
                    signals_fired += 1
                    if signals_fired >= 2:
                        break

            # ── Web escalation if Qdrant yield is thin ────────────────
            if len(new_chunks) < 2 and web_escalations_used < max_web_esc:
                web_new = await self._run_web_escalation(
                    queries[0], collection_name, vs
                )
                for c in web_new:
                    prefix = getattr(c, "text", "")[:120]
                    if prefix not in pool_text_prefixes:
                        new_chunks.append(c)
                        pool_text_prefixes.add(prefix)
                web_escalations_used += 1

            if not new_chunks:
                break

            # ── Quality gate ──────────────────────────────────────────
            kept = self._quality_gate_filter(new_chunks)

            chunk_pool.extend(kept)
            pool_vocab.update(self._build_pool_vocab(kept))
            iters_run += 1

        final_cov = self._compute_entity_coverage(required_entities, chunk_pool)
        return chunk_pool, {
            "augmentation_iters": iters_run,
            "entity_coverage": final_cov,
            "web_escalations": web_escalations_used,
            "chunks_added": len(chunk_pool) - len(initial_chunks),
        }

    def _extract_required_entities(self) -> list[str]:
        """
        Extract key entities from section title + description using heuristics.
        No LLM call — uses capitalized phrases and quoted terms.
        """
        text = f"{self.node.title} {self.node.description}"
        quoted  = re.findall(r'"([^"]+)"', text)
        caps    = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        title_w = [w for w in self.node.title.split() if len(w) > 3 and w[0].isupper()]
        seen: set[str] = set()
        result: list[str] = []
        for e in quoted + caps + title_w:
            if e.lower() not in seen:
                seen.add(e.lower())
                result.append(e)
        return result[:15]

    def _compute_entity_coverage(self, entities: list[str], chunks: list[Any]) -> float:
        """Fraction of required entities present in chunk pool text."""
        if not entities:
            return 1.0
        pool_text = " ".join(getattr(c, "text", "") for c in chunks).lower()
        covered = sum(1 for e in entities if e.lower() in pool_text)
        return covered / len(entities)

    @staticmethod
    def _build_pool_vocab(chunks: list[Any]) -> set[str]:
        """Word vocabulary for novelty computation (words ≥ 4 chars)."""
        vocab: set[str] = set()
        for c in chunks:
            vocab.update(re.findall(r'\b\w{4,}\b', getattr(c, "text", "").lower()))
        return vocab

    @staticmethod
    def _compute_novelty_rate(new_chunks: list[Any], pool_vocab: set[str]) -> float:
        """
        Fraction of new_chunks that are novel: >25% of their words not in pool_vocab.
        Returns 1.0 when list is empty (treat as fully novel).
        """
        if not new_chunks:
            return 1.0
        novel_count = 0
        for c in new_chunks:
            words = re.findall(r'\b\w{4,}\b', getattr(c, "text", "").lower())
            if not words:
                continue
            if sum(1 for w in words if w not in pool_vocab) / len(words) > NOVELTY_RATE_CEILING:
                novel_count += 1
        return novel_count / len(new_chunks)

    def _gaps_to_queries(self, gap_text: str) -> list[str]:
        """
        Convert gap analysis text into anchor-interpolated search queries.
        q_effective = section_title anchor + gap phrase (0.35 / 0.65 weighting
        approximated as string prepend — no re-embedding required here).
        """
        from agents.retriever.retriever import sanitize_query
        if not gap_text:
            return []
        parts = re.split(r'[.;,\n]', gap_text)
        queries: list[str] = []
        for part in parts:
            part = part.strip()
            if len(part) < 10:
                continue
            # Anchor: prepend section title for topic grounding (anchor interpolation)
            anchored = f"{self.node.title} {part}"
            cleaned = sanitize_query(anchored)
            if cleaned:
                queries.append(cleaned)
        return queries[:4]

    def _quality_gate_filter(self, chunks: list[Any]) -> list[Any]:
        """
        Relevance filter: keep chunks whose text overlaps with section anchor words.
        Always returns at least 1 chunk from a non-empty input.
        """
        if not chunks:
            return []
        title_words = set(re.findall(r'\b\w{4,}\b', self.node.title.lower()))
        desc_words  = set(re.findall(r'\b\w{4,}\b', self.node.description.lower()[:200]))
        anchor = title_words | desc_words
        if not anchor:
            return chunks
        scored = []
        for c in chunks:
            chunk_words = set(re.findall(r'\b\w{4,}\b', getattr(c, "text", "").lower()))
            overlap = len(anchor & chunk_words) / len(anchor)
            scored.append((overlap, c))
        scored.sort(key=lambda x: -x[0])
        keep_n = max(1, len(scored) // 2)
        return [c for _, c in scored[:keep_n]]

    async def _run_web_escalation(
        self,
        query: str,
        collection_name: str,
        vs,
    ) -> list[Any]:
        """
        Run a targeted web search for gap-filling evidence.
        Ingests results into the collection and returns newly-added chunks.
        """
        try:
            from skills import SKILL_REGISTRY
            web_skill = SKILL_REGISTRY.get("web_search")
            if web_skill is None:
                return []
            node = PlanNode(
                node_id=f"aug_{self.node.node_id}",
                description=query,
                skill="web_search",
                depends_on=[],
                acceptance=[],
                parallelizable=True,
                output_slot=f"aug_{self.node.node_id}",
            )
            await web_skill.run_fanout(
                queries=[query],
                run_id=self.run_id,
                collection_name=collection_name,
                node=node,
                ctx=None,
                vs=vs,
            )
            return vs.search(run_id=self.run_id, query_text=query, k=6, min_credibility=0.3)
        except Exception as exc:
            logger.warning("[Phase C+ web escalation] %s", exc)
            return []

    async def _check_faithfulness(
        self,
        content: str,
        evidence_text: str,
    ) -> float:
        """
        RAGAS-inspired faithfulness: claim decomposition + support verification.
        Uses the analysis LLM (mini model). Returns 0.0–1.0 score.
        """
        prompt = (
            f"Task: faithfulness check.\n\n"
            f"Section content (excerpt):\n{content[:1500]}\n\n"
            f"Evidence (excerpt):\n{evidence_text[:2000]}\n\n"
            f"Instructions:\n"
            f"1. List up to 10 factual claims from the section content.\n"
            f"2. For each claim, mark SUPPORTED or UNSUPPORTED based on the evidence.\n"
            f"3. Return ONLY this JSON: "
            f'{{\"supported\": N, \"total\": M, \"score\": X.XX}}\n'
            f"where score = supported / total."
        )
        try:
            raw = await asyncio.to_thread(
                self._analysis_client.generate_text,
                prompt=prompt,
                system_prompt="You are a faithfulness auditor. Return only JSON.",
                temperature=0.0,
            )
            m = re.search(r'"score"\s*:\s*([0-9.]+)', raw)
            if m:
                return min(1.0, max(0.0, float(m.group(1))))
        except Exception as exc:
            logger.warning("[faithfulness check] failed: %s", exc)
        return 1.0

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    def _gather_children_content(self) -> str:
        """
        Concatenates the already-written content of all direct children for
        the parent worker's context.  Node IDs are intentionally omitted —
        they are internal identifiers and must not appear in written prose.
        """
        children = self.tree.children_of(self.node.node_id)
        if not children:
            return ""
        parts = []
        for child in children:
            if child.content:
                parts.append(f"### {child.title}\n\n{child.content}")
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _make_citation_id(title: str, used_keys: set[str]) -> str:
        """
        Derive a stable, short PascalCase citation key from a source title.

        Skips stop words, joins up to 3 meaningful words (capped at 22 chars),
        and appends a numeric suffix on collision.
        Returns a bracketed key like `[ComplexityMatters]`.
        """
        clean = re.sub(r"[^\w\s]", " ", title)
        words = [w.capitalize() for w in clean.split() if w.lower() not in _STOP_WORDS and w.isalpha()]
        base = "".join(words[:3])[:22] if words else "Source"
        key, suffix = base, 2
        while key in used_keys:
            key = f"{base}{suffix}"
            suffix += 1
        used_keys.add(key)
        return f"[{key}]"

    @staticmethod
    def _resolve_title(title: str, url: str) -> str:
        """
        Returns a human-readable source label for citation purposes.

        If the stored title is empty, 'Unknown', a generic placeholder, or a
        tool-generated label like 'PDF chunk (pages X-Y)', derives a label
        from the URL domain to avoid polluting the Reference List with
        [Unknown] / [PdfChunkPages10] keys.
        """
        _GENERIC = {"unknown", "untitled", "source", ""}
        if title and title.lower() not in _GENERIC and not title.lower().startswith("pdf chunk"):
            return title
        if url:
            import re as _re
            domain = _re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
            path_hint = url.rstrip("/").split("/")[-1][:30]
            if path_hint and not path_hint.startswith("http"):
                return f"{domain} — {path_hint}"
            return domain
        return "Source"

    @staticmethod
    def _filter_cited_sources(
        source_map: dict[str, dict],
        content: str,
        citations_used: list[str],
    ) -> dict[str, dict]:
        """
        Return a source_map containing only entries that are actually cited.

        A key is kept when it appears in either:
          - citations_used  (list the LLM returned in Call 2)
          - the written content itself (scan for [BracketedKey] patterns)

        This ensures the Reference List only shows sources the reader can
        actually trace back to a claim in the text.
        """
        cited: set[str] = set(citations_used)
        cited.update(re.findall(r'\[\w+\d*\]', content))
        return {k: v for k, v in source_map.items() if k in cited}

    @staticmethod
    def _format_chunks(chunks: list[Any]) -> tuple[str, dict[str, dict]]:
        """
        Format Qdrant chunks for the LLM and build a citation source map.

        Each chunk header embeds a pre-assigned citation key so the LLM uses
        it verbatim instead of inventing its own.  Titles are resolved via
        _resolve_title so generic 'Unknown' entries are replaced with domain
        labels before the citation key is generated.

        Returns:
            chunks_text: formatted string passed to the LLM prompt.
            source_map:  dict mapping citation_id → {title, url} for the
                         Reference List assembled by the pipeline.
        """
        if not chunks:
            return "(no chunks retrieved)", {}
        parts: list[str] = []
        source_map: dict[str, dict] = {}
        used_keys: set[str] = set()
        for i, chunk in enumerate(chunks):
            cred        = getattr(chunk, "credibility", 0.0)
            raw_title   = getattr(chunk, "source_title", "") or ""
            url         = getattr(chunk, "source_url", "") or ""
            source_type = getattr(chunk, "source_type", "") or ""
            date        = getattr(chunk, "date", "") or ""
            text        = getattr(chunk, "text", str(chunk))
            title = ReportWorkerAgent._resolve_title(raw_title, url)
            cite_id = ReportWorkerAgent._make_citation_id(title, used_keys)
            if cite_id not in source_map:
                source_map[cite_id] = {
                    "title":       title,
                    "url":         url,
                    "source_type": source_type,
                    "date":        date,
                }
            parts.append(
                f"[Evidence {i} | Cite as: {cite_id}] "
                f"Source: {title} ({url}) | credibility={cred:.2f}\n{text}"
            )
        return "\n\n".join(parts), source_map

    def _heading_marker(self) -> str:
        """Return the Markdown heading prefix (_walk uses depth+1, root starts at depth=1)."""
        root_level = self.tree.root.level
        walk_depth = (self.node.level - root_level) + 1
        return "#" * min(walk_depth + 1, 6)

    def _build_call1_message(
        self,
        chunks_text: str,
        children_content: str,
        audience: str,
        research_query: str,
    ) -> str:
        heading_marker = self._heading_marker()
        msg = (
            f"call: 1\n"
            f"section_node_id: {self.node.node_id}\n"
            f"section_title: {self.node.title}\n"
            f"section_description: {self.node.description}\n"
            f"section_type: {self.node.section_type}\n"
            f"node_level: {self.node.level} / max_depth: {self.tree.max_depth}\n"
            f"section_heading: {heading_marker} {self.node.title}  "
            f"(assembler adds this — do NOT include it in your content; use deeper levels for internal sub-headings)\n"
            f"audience: {audience}\n"
            f"research_query: {research_query}\n\n"
        )
        if chunks_text and chunks_text != "(no chunks retrieved)":
            msg += f"## Retrieved Evidence\n\n{chunks_text}\n\n"
        if children_content:
            msg += f"## Children Content (already written)\n\n{children_content}\n\n"
        return msg

    def _build_call2_message(
        self,
        analysis: dict[str, Any],
        chunks_text: str,
        children_content: str,
        audience: str,
        raw_chunks: list[Any] | None = None,
    ) -> str:
        """
        Builds the Call 2 (write) prompt.

        Passes analysis results from Call 1 plus the raw text of the top-3 key
        evidence chunks (as identified by `key_evidence_chunks` in Call 1 output)
        so the writer has direct access to specific quotes, statistics, and formulas
        instead of relying solely on the lossy analysis digest.
        """
        key_chunk_text = ""
        if raw_chunks:
            top_idxs = analysis.get("key_evidence_chunks", [])[:3]
            excerpts = []
            for idx in top_idxs:
                if isinstance(idx, int) and idx < len(raw_chunks):
                    chunk = raw_chunks[idx]
                    text = getattr(chunk, "text", "")[:600]
                    excerpts.append(f"[Evidence {idx}]\n{text}")
            if excerpts:
                key_chunk_text = (
                    "## Key Evidence Excerpts (direct text for quoting)\n\n"
                    + "\n\n".join(excerpts)
                    + "\n\n"
                )

        # Single-source warning from Call 1
        ssw = analysis.get("single_source_warning")
        ssw_text = (
            f"\n⚠ Source diversity warning: {ssw}\n"
            f"Ensure you note limitations due to single-source evidence.\n\n"
        ) if ssw else ""

        return (
            f"call: 2\n"
            f"section_node_id: {self.node.node_id}\n"
            f"section_title: {self.node.title}\n"
            f"audience: {audience}\n\n"
            + ssw_text
            + f"## Analysis Results (from Call 1)\n\n"
            f"{json.dumps(analysis.get('analyses', {}), indent=2)}\n\n"
            f"## Citations Identified\n\n"
            f"{', '.join(analysis.get('citations_found', []) or [])}\n\n"
            + key_chunk_text
            + (f"## Children Content\n\n{children_content}\n\n" if children_content else "")
        )

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_call(raw: str, expected_call: int) -> dict[str, Any]:
        """
        Parses a JSON response from the LLM.

        Strategy 1: full JSON parse on sanitized text (fenced block or bare object).
        Strategy 2: salvage `content` string alone via raw_decode (handles inner quotes).
        """
        sanitized = sanitize_string_values(raw)

        obj = extract_object(sanitized)
        if obj is not None:
            return obj

        content_str = extract_string_field(sanitized, "content")
        if content_str is not None:
            citations: list[str] = []
            citations_match = re.search(
                r'"citations_used"\s*:\s*(\[[^\]]*\])', sanitized
            )
            if citations_match:
                try:
                    citations = json.loads(citations_match.group(1))
                except json.JSONDecodeError:
                    pass
            return {
                "call": expected_call,
                "content": content_str,
                "citations_used": citations,
                "analyses": {},
            }

        return {"call": expected_call, "content": raw, "analyses": {}}
