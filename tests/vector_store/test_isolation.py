import pytest

from vector_store import RetrievalScope, VectorStoreClient


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        return [0.1] * 384

    def chunk_and_embed(self, text: str) -> list[tuple[str, list[float]]]:
        return [(text, self.embed(text))]


def _store() -> VectorStoreClient:
    return VectorStoreClient(force_in_memory=True, embedder=FakeEmbedder())


def test_shared_collection_never_returns_another_users_chunks() -> None:
    store = _store()
    store.ingest_text(
        scope=RetrievalScope(user_id="user_a", conversation_id="chat_a"),
        text="Modal is used for worker execution.",
        source_type="chat_memory",
        document_id="doc_a",
    )
    store.ingest_text(
        scope=RetrievalScope(user_id="user_b", conversation_id="chat_b"),
        text="Modal is used for worker execution.",
        source_type="chat_memory",
        document_id="doc_b",
    )

    results = store.search(
        scope=RetrievalScope(user_id="user_a", conversation_id="chat_a"),
        query_text="How is worker execution handled?",
        limit=8,
    )

    assert len(results) == 1
    assert results[0].scope.user_id == "user_a"
    assert results[0].scope.conversation_id == "chat_a"
    assert results[0].document_id == "doc_a"


def test_scope_filter_cannot_be_omitted_or_widened_after_ingestion() -> None:
    store = _store()
    with pytest.raises(ValueError, match="user_id"):
        RetrievalScope(user_id="")

    store.ingest_text(
        scope=RetrievalScope(user_id="user_a", report_id="report_a"),
        text="Private report evidence.",
        source_type="report",
        document_id="report_a:v1",
    )

    results = store.search(
        scope=RetrievalScope(user_id="user_b", report_id="report_a"),
        query_text="Private evidence",
    )
    assert results == []


def test_search_requires_a_typed_scope_not_untrusted_filters() -> None:
    store = _store()
    with pytest.raises(TypeError):
        store.search(query_text="anything")  # type: ignore[call-arg]


def test_reingesting_a_document_upserts_instead_of_creating_duplicate_chunks() -> None:
    store = _store()
    scope = RetrievalScope(user_id="user_a", research_run_id="run_a")
    kwargs = {
        "scope": scope,
        "text": "A source record that may be revisited after a worker retry.",
        "source_type": "web",
        "document_id": "https://example.test/source",
    }

    first = store.ingest_text(**kwargs)
    second = store.ingest_text(**kwargs)
    results = store.search(scope=scope, query_text="worker retry source", limit=8)

    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert len(results) == 1
    assert results[0].document_id == kwargs["document_id"]
