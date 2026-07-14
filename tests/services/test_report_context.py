"""Ingesting a finalized report and retrieving it as report-linked chat context."""
from __future__ import annotations

from api.services.report_context import REPORT_SOURCE_TYPE, ingest_report_content
from vector_store import RetrievalScope, VectorStoreClient


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        return [0.1] * 384

    def chunk_and_embed(self, text: str) -> list[tuple[str, list[float]]]:
        return [(text, self.embed(text))]


def _store() -> VectorStoreClient:
    return VectorStoreClient(force_in_memory=True, embedder=FakeEmbedder())


def test_ingested_report_is_retrievable_under_its_user_and_report_scope() -> None:
    store = _store()
    ingest_report_content(
        store,
        user_id="user_a",
        report_id="report_a",
        version_number=1,
        content="The quarterly revenue grew 20% driven by enterprise contracts.",
        title="Q3 report",
    )

    results = store.search(
        scope=RetrievalScope(user_id="user_a", report_id="report_a"),
        query_text="how did revenue change",
        limit=8,
    )

    assert len(results) == 1
    assert results[0].source_type == REPORT_SOURCE_TYPE
    assert "enterprise contracts" in results[0].text
    assert results[0].scope.report_id == "report_a"


def test_report_context_is_isolated_from_other_reports_and_users() -> None:
    store = _store()
    ingest_report_content(
        store, user_id="user_a", report_id="report_a", version_number=1, content="Report A content."
    )
    ingest_report_content(
        store, user_id="user_a", report_id="report_b", version_number=1, content="Report B content."
    )
    ingest_report_content(
        store, user_id="user_b", report_id="report_a", version_number=1, content="Other user content."
    )

    results = store.search(
        scope=RetrievalScope(user_id="user_a", report_id="report_a"),
        query_text="content",
        limit=8,
    )

    assert len(results) == 1
    assert results[0].text == "Report A content."


def test_reingesting_a_report_upserts_instead_of_duplicating() -> None:
    store = _store()
    first = ingest_report_content(
        store, user_id="user_a", report_id="report_a", version_number=1, content="First finalization."
    )
    second = ingest_report_content(
        store, user_id="user_a", report_id="report_a", version_number=2, content="First finalization."
    )

    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    results = store.search(
        scope=RetrievalScope(user_id="user_a", report_id="report_a"),
        query_text="finalization",
        limit=8,
    )
    assert len(results) == 1


def test_empty_report_content_is_not_ingested() -> None:
    store = _store()
    assert ingest_report_content(
        store, user_id="user_a", report_id="report_a", version_number=1, content="   "
    ) == []
