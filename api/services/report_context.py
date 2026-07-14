"""Ingest a finalized report into the tenant-scoped vector store.

A report is embedded once it is produced finally (the research workflow
finishes and a report version is stored). Every chunk carries the owning
``user_id`` and the ``report_id`` in its payload, so retrieval for a
report-linked chat pulls context for that report only, and never crosses to
another report or another user.
"""
from __future__ import annotations

from typing import Protocol

from vector_store.models import DocumentChunk, RetrievalScope

REPORT_SOURCE_TYPE = "report"


class ReportVectorStore(Protocol):
    def ingest_text(
        self,
        *,
        scope: RetrievalScope,
        text: str,
        source_type: str,
        document_id: str,
        source_url: str = ...,
        source_title: str = ...,
        credibility: float = ...,
        metadata: dict | None = ...,
    ) -> list[DocumentChunk]: ...


def ingest_report_content(
    vector_store: ReportVectorStore,
    *,
    user_id: str,
    report_id: str,
    version_number: int,
    content: str,
    title: str = "",
) -> list[DocumentChunk]:
    """Embed a finalized report version under its ``{user_id, report_id}`` scope.

    The ``document_id`` is version-stable so a later finalization of the same
    report upserts its chunks rather than accumulating duplicates. Returns the
    ingested chunks (empty when the report has no textual content).
    """
    text = (content or "").strip()
    if not text:
        return []
    scope = RetrievalScope(user_id=user_id, report_id=report_id)
    return vector_store.ingest_text(
        scope=scope,
        text=text,
        source_type=REPORT_SOURCE_TYPE,
        document_id=f"report:{report_id}",
        source_title=title or "",
        credibility=1.0,
        metadata={"version_number": version_number},
    )
