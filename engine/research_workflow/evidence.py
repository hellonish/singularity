from __future__ import annotations

import hashlib
from typing import Any

from vector_store.models import RetrievalScope


def rank_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order evidence so the most substantial records survive downstream caps.

    Both the resolver and the answerer truncate evidence to a per-node budget,
    so list order decides what the model actually sees. Records are
    deduplicated by URL (keeping the one with the most content — a fetched
    page over its search snippet) and sorted so full-text extractions rank
    ahead of snippets, with source credibility breaking ties. Content length
    is bucketed to the nearest 1,000 characters so a marginally longer snippet
    does not outrank a more credible one.
    """
    by_url: dict[str, dict[str, Any]] = {}
    unkeyed: list[dict[str, Any]] = []
    for item in evidence:
        url = str(item.get("url", ""))
        if not url:
            unkeyed.append(item)
            continue
        current = by_url.get(url)
        if current is None or len(str(item.get("content", ""))) > len(str(current.get("content", ""))):
            by_url[url] = item

    def rank_key(item: dict[str, Any]) -> tuple[int, float]:
        content_bucket = len(str(item.get("content", ""))) // 1_000
        try:
            credibility = float(item.get("credibility") or 0.0)
        except (TypeError, ValueError):
            credibility = 0.0
        return (content_bucket, credibility)

    return sorted([*by_url.values(), *unkeyed], key=rank_key, reverse=True)


def persist_evidence(*, vector_store, scope: RetrievalScope, node_id: str, evidence: list[dict[str, Any]], answer: dict[str, Any]) -> dict[str, Any]:
    """Persist source text and a lineage-linked synthetic answer.

    The answer is deliberately marked synthetic in payload metadata through its
    source type. Callers must use the original source records for citations.
    """
    source_ids: list[str] = []
    stored_sources: list[dict[str, Any]] = []
    for item in evidence:
        text = (item.get("content") or item.get("snippet") or "").strip()
        url = (item.get("url") or "").strip()
        if not text:
            continue
        document_id = hashlib.sha256((url or text[:200]).encode()).hexdigest()[:32]
        vector_store.ingest_text(
            scope=scope,
            text=text,
            source_type=str(item.get("source_type") or "web"),
            document_id=document_id,
            source_url=url,
            source_title=str(item.get("title") or ""),
            credibility=float(item.get("credibility", 0.5)),
        )
        source_ids.append(document_id)
        stored_sources.append({
            "document_id": document_id,
            "title": str(item.get("title") or ""),
            "url": url,
            "source_type": str(item.get("source_type") or "web"),
            "date": item.get("date"),
        })

    answer_text = str(answer.get("answer") or answer.get("summary") or "").strip()
    if answer_text:
        vector_store.ingest_text(
            scope=scope,
            text=answer_text,
            source_type="synthetic_research_answer",
            document_id=f"answer:{node_id}",
            source_url="",
            source_title=f"Research answer {node_id}",
            credibility=0.0,
            metadata={
                "synthetic": True,
                "node_id": node_id,
                "source_document_ids": source_ids,
            },
        )
    return {
        "source_ids": source_ids,
        "source_records": stored_sources,
        "answer_document_id": f"answer:{node_id}",
    }
