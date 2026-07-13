from __future__ import annotations

import hashlib
from typing import Any

from vector_store.models import RetrievalScope


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
