"""
SourceGate — 2-pass source relevance filter.

Sits between _fetch() and Qdrant ingestion in BaseRetrievalSkill.run_fanout().

Pass 1  (local, zero cost):
    Embed all source snippets + the original research query with the same
    all-MiniLM-L6-v2 model used by the vector store.  Since embeddings are
    L2-normalised, cosine similarity = dot product.  Sources below
    PASS1_THRESHOLD are discarded before any LLM token is spent.

Pass 2  (one Grok call per skill, aggregate):
    All Pass-1 survivors from every query for the current skill are sent in
    a single structured Grok call.  The model returns approved_urls — the
    subset that is unambiguously about the entity/topic in the original query.
    Fallback: if the call fails or returns no URLs, all survivors are kept.
"""
from __future__ import annotations

import asyncio
import logging

import numpy as np
from pydantic import BaseModel

from vector_store.embedder import Embedder

logger = logging.getLogger(__name__)

PASS1_THRESHOLD  = 0.35   # cosine similarity floor; below = off-topic
SNIPPET_MAX_CHARS = 300   # max characters from each source excerpt for embedding + gating

# ---------------------------------------------------------------------------
# Shared embedder instance (model is loaded once globally in embedder.py)
# ---------------------------------------------------------------------------

_embedder: Embedder | None = None


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


# ---------------------------------------------------------------------------
# Pass 1 — embedding cosine similarity filter
# ---------------------------------------------------------------------------

def pass1_filter(
    sources: list[dict],
    original_query: str,
    threshold: float = PASS1_THRESHOLD,
) -> list[dict]:
    """
    Filter sources whose snippet is below `threshold` cosine similarity to
    the original research query.

    Fallback: returns all sources unchanged when:
      - all snippets are empty (nothing to embed)
      - every source scores below threshold (avoid starving the pipeline)
    """
    if not sources:
        return sources

    snippets = [
        (src.get("content") or src.get("snippet") or src.get("abstract") or "")[:SNIPPET_MAX_CHARS]
        for src in sources
    ]
    non_empty = [(i, s) for i, s in enumerate(snippets) if s.strip()]
    if not non_empty:
        return sources  # nothing to compare — pass all

    indices, texts = zip(*non_empty)
    embedder = _get_embedder()

    # One batch call: [query] + all snippets
    all_vecs = np.array(
        embedder.embed_batch([original_query] + list(texts))
    )                                # shape (N+1, 384)

    q_vec   = all_vecs[0]           # (384,)
    src_vecs = all_vecs[1:]         # (N, 384)
    sims     = src_vecs @ q_vec     # (N,) — dot product == cosine sim (normalised)

    survivors = [sources[i] for i, sim in zip(indices, sims) if sim >= threshold]
    return survivors if survivors else sources   # fallback: never empty


# ---------------------------------------------------------------------------
# Pass 2 — aggregate Grok gate
# ---------------------------------------------------------------------------

class _GateOutput(BaseModel):
    approved_urls: list[str]


async def pass2_gate(
    gate_client,
    original_query: str,
    survivors: list[tuple[dict, str]],  # (source_dict, sub_query)
) -> set[str]:
    """
    One structured Grok call for all Pass-1 survivors across every query in
    the current skill.  Returns the set of approved source URLs.

    Fallback: returns all survivor URLs on any exception so the pipeline
    never silently drops valid content.
    """
    if not survivors:
        return set()

    lines: list[str] = []
    for i, (src, _sub_q) in enumerate(survivors):
        excerpt = (
            src.get("content") or src.get("snippet") or src.get("abstract") or ""
        )[:150]
        lines.append(
            f"[{i}] url={src.get('url', '')} | "
            f"title={src.get('title', '')[:80]} | "
            f"excerpt={excerpt}"
        )

    system_prompt = (
        "You are a source relevance gate. Given a research query and a list of "
        "retrieved web sources, return only the URLs of sources that are directly "
        "and unambiguously relevant to the specific entity, product, or topic named "
        "in the research query. Reject sources about different entities that merely "
        "share a name or keyword with the query. When genuinely unsure, include the "
        "source — do not over-filter legitimate results."
    )
    user_prompt = (
        f"research_query: {original_query}\n\n"
        f"sources ({len(lines)} total):\n" + "\n".join(lines)
    )

    try:
        result = await asyncio.to_thread(
            gate_client.generate_structured,
            user_prompt,
            system_prompt,
            _GateOutput,
            0.1,
        )
        return set(result.approved_urls)
    except Exception as exc:
        logger.warning("[SourceGate Pass2] gate call failed (%s) — passing all survivors", exc)
        return {src.get("url", "") for src, _ in survivors}
