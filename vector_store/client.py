"""
VectorStoreClient — Qdrant wrapper for the research pipeline.

Responsibilities:
  - Create / delete per-run collections
  - Ingest DocumentChunk objects (with embedding)
  - Semantic search returning DocumentChunk objects
  - Topic-cache index: detect near-duplicate queries across runs
  - Collection TTL cleanup
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any

from models import DocumentChunk
from .config import (
    COLLECTION_CONFIG,
    TOPIC_CACHE_COLLECTION,
    TOPIC_CACHE_SIMILARITY_THRESHOLD,
    TOPIC_CACHE_TTL_DAYS,
)
from .embedder import Embedder

_QDRANT_URL     = os.getenv("QDRANT_URL", "http://localhost:6333")
_QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
_UPSERT_BATCH   = 64   # points per upsert call


class VectorStoreClient:
    """
    Thin wrapper around qdrant-client.  Lazy-initialises the client on first
    use so the module can be imported without qdrant running.
    """

    def __init__(self) -> None:
        self._qdrant = None
        self._in_memory = False
        self._embedder = Embedder()

    # ------------------------------------------------------------------
    # Lazy client init
    # ------------------------------------------------------------------

    @property
    def qdrant(self):
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            # Try connecting to the configured server; fall back to in-memory
            try:
                kwargs: dict[str, Any] = {"url": _QDRANT_URL, "timeout": 3}
                if _QDRANT_API_KEY:
                    kwargs["api_key"] = _QDRANT_API_KEY
                client = QdrantClient(**kwargs)
                client.get_collections()   # probe — raises if server is down
                self._qdrant = client
                self._in_memory = False
            except Exception:
                self._qdrant = QdrantClient(":memory:")
                self._in_memory = True
                print("[VectorStore] Qdrant server unavailable — using in-memory mode")
        return self._qdrant

    # ------------------------------------------------------------------
    # Collection lifecycle
    # ------------------------------------------------------------------

    def create_collection(self, run_id: str) -> str:
        """Create a fresh collection for this run. Returns collection name."""
        from qdrant_client.models import VectorParams, Distance
        name = f"run_{run_id}"
        self.qdrant.recreate_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=COLLECTION_CONFIG["size"],
                distance=Distance.COSINE,
            ),
        )
        return name

    def delete_collection(self, run_id: str) -> None:
        name = f"run_{run_id}"
        try:
            self.qdrant.delete_collection(name)
        except Exception:
            pass

    def ensure_topic_cache_index(self) -> None:
        """Create the topic-cache meta-collection if it doesn't exist."""
        from qdrant_client.models import VectorParams, Distance
        existing = {c.name for c in self.qdrant.get_collections().collections}
        if TOPIC_CACHE_COLLECTION not in existing:
            self.qdrant.create_collection(
                collection_name=TOPIC_CACHE_COLLECTION,
                vectors_config=VectorParams(
                    size=COLLECTION_CONFIG["size"],
                    distance=Distance.COSINE,
                ),
            )

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def ingest_chunks(self, collection_name: str, chunks: list[DocumentChunk]) -> None:
        """
        Upsert DocumentChunk objects into the collection.
        Chunks must already have embeddings set.
        """
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=chunk.id,
                vector=chunk.embedding,
                payload={k: v for k, v in chunk.to_qdrant_point()["payload"].items()},
            )
            for chunk in chunks
        ]
        # Batch upsert to avoid large payloads
        for i in range(0, len(points), _UPSERT_BATCH):
            self.qdrant.upsert(
                collection_name=collection_name,
                points=points[i : i + _UPSERT_BATCH],
            )

    def ingest_text(
        self,
        collection_name: str,
        text: str,
        run_id: str,
        source_url: str,
        source_title: str,
        credibility: float,
        skill: str,
        query: str,
    ) -> list[DocumentChunk]:
        """
        Chunk, embed, and ingest a raw text document.
        Returns the list of DocumentChunk objects created.
        """
        chunk_embeddings = self._embedder.chunk_and_embed(text)
        chunks = [
            DocumentChunk(
                text=chunk_text,
                embedding=embedding,
                source_url=source_url,
                source_title=source_title,
                credibility=credibility,
                skill=skill,
                query=query,
                run_id=run_id,
                chunk_index=idx,
            )
            for idx, (chunk_text, embedding) in enumerate(chunk_embeddings)
        ]
        if chunks:
            self.ingest_chunks(collection_name, chunks)
        return chunks

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        run_id: str,
        query_text: str,
        k: int = 15,
        min_credibility: float = 0.5,
    ) -> list[DocumentChunk]:
        """
        Semantic search in the run's collection.
        Returns up to k chunks sorted by relevance descending.
        """
        from qdrant_client.models import Filter, FieldCondition, Range

        query_embedding = self._embedder.embed(query_text)
        response = self.qdrant.query_points(
            collection_name=f"run_{run_id}",
            query=query_embedding,
            limit=k,
            with_payload=True,
            with_vectors=False,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="credibility",
                        range=Range(gte=min_credibility),
                    )
                ]
            ) if min_credibility > 0 else None,
        )
        return [DocumentChunk.from_qdrant_point(r) for r in response.points]

    def search_by_embedding(
        self,
        run_id: str,
        embedding: list[float],
        k: int = 15,
        min_credibility: float = 0.5,
    ) -> list[DocumentChunk]:
        """
        Semantic search using a pre-computed embedding vector.
        Used by Phase C+ anchor interpolation to query with blended embeddings.
        """
        from qdrant_client.models import Filter, FieldCondition, Range
        response = self.qdrant.query_points(
            collection_name=f"run_{run_id}",
            query=embedding,
            limit=k,
            with_payload=True,
            with_vectors=False,
            query_filter=Filter(
                must=[FieldCondition(key="credibility", range=Range(gte=min_credibility))]
            ) if min_credibility > 0 else None,
        )
        return [DocumentChunk.from_qdrant_point(r) for r in response.points]

    def count_chunks(self, run_id: str, query_text: str, k: int = 200) -> int:
        """
        Approximate chunk count for a section query via broad search.
        Used by Layer 1 coverage audit to detect starved sections.
        """
        chunks = self.search(run_id=run_id, query_text=query_text, k=k, min_credibility=0.0)
        return len(chunks)

    # ------------------------------------------------------------------
    # Topic cache
    # ------------------------------------------------------------------

    def find_cached_run(self, query: str) -> str | None:
        if self._in_memory:
            return None   # no cross-run cache in memory mode
        """
        Returns a cached collection name (run_id) if a semantically similar
        query was run recently (within TTL), else None.
        """
        self.ensure_topic_cache_index()
        query_embedding = self._embedder.embed(query)
        response = self.qdrant.query_points(
            collection_name=TOPIC_CACHE_COLLECTION,
            query=query_embedding,
            limit=1,
            with_payload=True,
            score_threshold=TOPIC_CACHE_SIMILARITY_THRESHOLD,
        )
        if not response.points:
            return None

        point = response.points[0]
        created_at_str = point.payload.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str)
            age_days = (datetime.now(timezone.utc) - created_at).days
            if age_days < TOPIC_CACHE_TTL_DAYS:
                return point.payload.get("run_id")
        except (ValueError, TypeError):
            pass
        return None

    def register_run_in_cache(self, run_id: str, query: str) -> None:
        if self._in_memory:
            return   # nothing to persist in memory mode
        """Index this run's query embedding so future runs can cache-hit it."""
        import uuid
        from qdrant_client.models import PointStruct

        self.ensure_topic_cache_index()
        embedding = self._embedder.embed(query)
        self.qdrant.upsert(
            collection_name=TOPIC_CACHE_COLLECTION,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "run_id":     run_id,
                        "query":      query,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            ],
        )

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def cleanup_expired_collections(self) -> list[str]:
        """
        Delete run collections older than TTL.
        Returns list of deleted collection names.
        """
        self.ensure_topic_cache_index()
        cutoff = datetime.now(timezone.utc) - timedelta(days=TOPIC_CACHE_TTL_DAYS)
        deleted: list[str] = []

        # Scroll all entries in the cache index
        offset = None
        while True:
            scroll_result = self.qdrant.scroll(
                collection_name=TOPIC_CACHE_COLLECTION,
                limit=100,
                offset=offset,
                with_payload=True,
            )
            points, next_offset = scroll_result
            for point in points:
                try:
                    created_at = datetime.fromisoformat(
                        point.payload.get("created_at", "")
                    )
                    if created_at < cutoff:
                        run_id = point.payload.get("run_id")
                        if run_id:
                            self.delete_collection(run_id)
                            deleted.append(f"run_{run_id}")
                except (ValueError, TypeError):
                    pass
            if next_offset is None:
                break
            offset = next_offset

        return deleted
