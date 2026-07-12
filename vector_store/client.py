"""Qdrant client with mandatory tenant-scoped ingestion and retrieval."""
from __future__ import annotations

import logging
import os
from typing import Any, Protocol
from urllib.parse import urlparse

from .config import (
    CHUNKS_COLLECTION,
    COLLECTION_CONFIG,
    FORCE_IN_MEMORY,
    PAYLOAD_INDEX_FIELDS,
    QDRANT_CONNECT_TIMEOUT,
    UPSERT_BATCH_SIZE,
)
from .embedder import Embedder
from .models import DocumentChunk, RetrievalScope

logger = logging.getLogger(__name__)
_QDRANT_URL = os.getenv("QDRANT_URL") or os.getenv("QDRANT_LOCATION") or "http://localhost:6333"


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...

    def chunk_and_embed(self, text: str) -> list[tuple[str, list[float]]]: ...


def _qdrant_connection_kwargs(url: str, timeout: int) -> dict[str, Any]:
    raw_key = (os.getenv("QDRANT_API_KEY") or "").strip()
    kwargs: dict[str, Any] = {"url": url.strip(), "timeout": timeout}
    if not raw_key:
        return kwargs
    parsed = urlparse(url.strip())
    if parsed.scheme == "http" and (parsed.hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}:
        return kwargs
    if parsed.scheme == "http":
        raise RuntimeError("QDRANT_URL must use https when QDRANT_API_KEY is configured")
    kwargs["api_key"] = raw_key
    return kwargs


class VectorStoreClient:
    """One shared collection; every operation requires a ``RetrievalScope``.

    This class intentionally exposes no unfiltered global search or caller-
    selected collection name.  Authorization remains the API service's job;
    this class enforces the resulting metadata boundary inside Qdrant.
    """

    def __init__(self, *, force_in_memory: bool = False, embedder: EmbeddingProvider | None = None) -> None:
        self._qdrant = None
        self._in_memory = FORCE_IN_MEMORY or force_in_memory
        self._embedder = embedder or Embedder()

    @property
    def qdrant(self):
        if self._qdrant is not None:
            return self._qdrant
        from qdrant_client import QdrantClient

        if self._in_memory:
            self._qdrant = QdrantClient(":memory:")
        else:
            self._qdrant = QdrantClient(**_qdrant_connection_kwargs(_QDRANT_URL, QDRANT_CONNECT_TIMEOUT))
            self._qdrant.get_collections()
        return self._qdrant

    def ensure_collection(self) -> None:
        from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

        existing = {collection.name for collection in self.qdrant.get_collections().collections}
        if CHUNKS_COLLECTION not in existing:
            self.qdrant.create_collection(
                collection_name=CHUNKS_COLLECTION,
                vectors_config=VectorParams(size=COLLECTION_CONFIG["size"], distance=Distance.COSINE),
            )
        for field_name in PAYLOAD_INDEX_FIELDS:
            try:
                self.qdrant.create_payload_index(
                    collection_name=CHUNKS_COLLECTION,
                    field_name=field_name,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception:
                # Existing indexes and in-memory Qdrant differ by version;
                # index creation is an optimization, never an authorization check.
                continue
        try:
            self.qdrant.create_payload_index(
                collection_name=CHUNKS_COLLECTION,
                field_name="credibility",
                field_schema=PayloadSchemaType.FLOAT,
            )
        except Exception:
            pass

    def ingest_text(
        self,
        *,
        scope: RetrievalScope,
        text: str,
        source_type: str,
        document_id: str,
        source_url: str = "",
        source_title: str = "",
        credibility: float = 0.5,
    ) -> list[DocumentChunk]:
        chunks = [
            DocumentChunk(
                text=chunk_text,
                embedding=embedding,
                scope=scope,
                source_type=source_type,
                document_id=document_id,
                source_url=source_url,
                source_title=source_title,
                credibility=credibility,
                chunk_index=index,
            )
            for index, (chunk_text, embedding) in enumerate(self._embedder.chunk_and_embed(text))
        ]
        self.ingest_chunks(scope=scope, chunks=chunks)
        return chunks

    def ingest_chunks(self, *, scope: RetrievalScope, chunks: list[DocumentChunk]) -> None:
        from qdrant_client.models import PointStruct

        if any(chunk.scope != scope for chunk in chunks):
            raise ValueError("every chunk must use the exact authorized retrieval scope")
        if not chunks:
            return
        self.ensure_collection()
        points = [PointStruct(id=chunk.id, vector=chunk.embedding, payload=chunk.payload()) for chunk in chunks]
        for offset in range(0, len(points), UPSERT_BATCH_SIZE):
            self.qdrant.upsert(collection_name=CHUNKS_COLLECTION, points=points[offset : offset + UPSERT_BATCH_SIZE])

    def search(
        self,
        *,
        scope: RetrievalScope,
        query_text: str,
        limit: int = 8,
        min_credibility: float = 0.0,
    ) -> list[DocumentChunk]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue, Range

        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        if not 0.0 <= min_credibility <= 1.0:
            raise ValueError("min_credibility must be between 0 and 1")
        self.ensure_collection()
        must = [
            FieldCondition(key=key, match=MatchValue(value=value))
            for key, value in scope.payload_filter().items()
        ]
        if min_credibility:
            must.append(FieldCondition(key="credibility", range=Range(gte=min_credibility)))
        response = self.qdrant.query_points(
            collection_name=CHUNKS_COLLECTION,
            query=self._embedder.embed(query_text),
            query_filter=Filter(must=must),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [DocumentChunk.from_qdrant_point(point) for point in response.points]
