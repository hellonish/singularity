"""
VectorStoreClient — Qdrant wrapper for the research pipeline.

Responsibilities:
  - Create / delete per-run collections
  - Ingest DocumentChunk objects (with embedding)
  - Semantic search returning DocumentChunk objects
  - Topic-cache index: detect near-duplicate queries across runs
  - Collection TTL cleanup (call cleanup_expired_collections after each run)

Connection modes:
  - Server mode (default): connects to QDRANT_URL; raises on failure.
  - In-memory mode: enabled by QDRANT_FORCE_IN_MEMORY=1 env var or by
    passing ``force_in_memory=True`` to the constructor.  Topic-cache and
    cross-run persistence are disabled in this mode.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from models import DocumentChunk
from .config import (
    COLLECTION_CONFIG,
    TOPIC_CACHE_COLLECTION,
    TOPIC_CACHE_SIMILARITY_THRESHOLD,
    TOPIC_CACHE_TTL_DAYS,
    QDRANT_CONNECT_TIMEOUT,
    FORCE_IN_MEMORY,
    UPSERT_BATCH_SIZE,
)
from .embedder import Embedder

_QDRANT_URL = os.getenv("QDRANT_URL") or os.getenv("QDRANT_LOCATION") or "http://localhost:6333"

_UPSERT_MAX_RETRIES = 3
_UPSERT_RETRY_DELAY = 1.0   # seconds between retries


def _qdrant_connection_kwargs(url: str, timeout: int) -> dict[str, Any]:
    """
    Build QdrantClient kwargs: avoid HTTP + api_key (library warns; key is cleartext).

    Local Docker Qdrant is usually open on http://localhost without auth — omit key.
    Qdrant Cloud and other remote hosts must use https:// when an API key is set.
    """
    raw_key = (os.getenv("QDRANT_API_KEY") or "").strip()
    kwargs: dict[str, Any] = {"url": url.strip(), "timeout": timeout}
    if not raw_key:
        return kwargs
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    local_hosts = frozenset({"localhost", "127.0.0.1", "::1"})
    if scheme == "http" and host in local_hosts:
        logger.info(
            "[VectorStore] HTTP localhost — omitting QDRANT_API_KEY (default Qdrant has no auth). "
            "For Qdrant Cloud set QDRANT_URL to https://…"
        )
        return kwargs
    if scheme == "http":
        raise RuntimeError(
            "[VectorStore] QDRANT_URL must use https:// when QDRANT_API_KEY is set "
            "(plain HTTP would expose the key). Update QDRANT_URL or clear the key for insecure dev only."
        )
    kwargs["api_key"] = raw_key
    return kwargs


class VectorStoreClient:
    """
    Thin wrapper around qdrant-client.  Lazy-initialises the Qdrant connection
    on first use so the module can be imported without a running Qdrant server.

    Args:
        force_in_memory: If True, always use an in-memory Qdrant instance.
            Overrides the QDRANT_FORCE_IN_MEMORY env variable.
    """

    def __init__(self, force_in_memory: bool = False) -> None:
        self._qdrant = None
        self._in_memory: bool = FORCE_IN_MEMORY or force_in_memory
        self._embedder = Embedder()

    # ------------------------------------------------------------------
    # Lazy client init
    # ------------------------------------------------------------------

    @property
    def qdrant(self):
        if self._qdrant is not None:
            return self._qdrant

        from qdrant_client import QdrantClient

        if self._in_memory:
            self._qdrant = QdrantClient(":memory:")
            logger.info("[VectorStore] Using in-memory Qdrant (persistence disabled).")
            return self._qdrant

        kwargs = _qdrant_connection_kwargs(_QDRANT_URL, QDRANT_CONNECT_TIMEOUT)

        try:
            client = QdrantClient(**kwargs)
            client.get_collections()   # probe — raises if server is unreachable
            self._qdrant = client
            logger.debug("[VectorStore] Connected to Qdrant at %s.", _QDRANT_URL)
        except Exception as exc:
            raise RuntimeError(
                f"[VectorStore] Cannot connect to Qdrant at {_QDRANT_URL!r}. "
                f"Start the server, fix QDRANT_URL, or set QDRANT_FORCE_IN_MEMORY=1 "
                f"for development. Original error: {exc}"
            ) from exc

        return self._qdrant

    # ------------------------------------------------------------------
    # Collection lifecycle
    # ------------------------------------------------------------------

    def create_collection(self, run_id: str) -> str:
        """Create a fresh collection for this run. Returns the collection name."""
        from qdrant_client.models import VectorParams, Distance, PayloadSchemaType
        name = f"run_{run_id}"
        self.qdrant.recreate_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=COLLECTION_CONFIG["size"],
                distance=Distance.COSINE,
            ),
        )
        # Qdrant Cloud requires explicit payload indexes for filtering.
        self.qdrant.create_payload_index(
            collection_name=name, field_name="credibility",
            field_schema=PayloadSchemaType.FLOAT,
        )
        return name

    def delete_collection(self, run_id: str) -> None:
        """Delete the collection for the given run_id.  Swallows errors (best-effort)."""
        name = f"run_{run_id}"
        try:
            self.qdrant.delete_collection(name)
        except Exception as exc:
            logger.debug("[VectorStore] delete_collection %s failed: %s", name, exc)

    def ensure_topic_cache_index(self) -> None:
        """Create the topic-cache meta-collection if it does not yet exist."""
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
        """Upsert DocumentChunk objects into the collection.

        Chunks must already have embeddings set.  Retries up to
        ``_UPSERT_MAX_RETRIES`` times on transient errors before raising.
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

        for i in range(0, len(points), UPSERT_BATCH_SIZE):
            batch = points[i : i + UPSERT_BATCH_SIZE]
            for attempt in range(_UPSERT_MAX_RETRIES):
                try:
                    self.qdrant.upsert(collection_name=collection_name, points=batch)
                    break
                except Exception as exc:
                    if attempt == _UPSERT_MAX_RETRIES - 1:
                        raise RuntimeError(
                            f"[VectorStore] upsert failed after {_UPSERT_MAX_RETRIES} "
                            f"attempts for collection {collection_name!r}: {exc}"
                        ) from exc
                    logger.warning(
                        "[VectorStore] upsert attempt %d/%d failed: %s — retrying in %.1fs",
                        attempt + 1, _UPSERT_MAX_RETRIES, exc, _UPSERT_RETRY_DELAY,
                    )
                    time.sleep(_UPSERT_RETRY_DELAY)

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
        """Chunk, embed, and ingest a raw text document.

        Returns the list of ``DocumentChunk`` objects created and stored.
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
        """Semantic search in the run's collection.

        Args:
            run_id:          The run whose collection to search.
            query_text:      Natural-language query to embed and search.
            k:               Maximum number of results to return.
            min_credibility: Minimum credibility score filter (0.0 = no filter).

        Returns:
            Up to ``k`` DocumentChunk objects sorted by relevance descending.
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
                must=[FieldCondition(key="credibility", range=Range(gte=min_credibility))]
            ) if min_credibility > 0 else None,
        )
        return [DocumentChunk.from_qdrant_point(r) for r in response.points]

    def count_chunks(self, run_id: str, query_text: str, k: int = 200) -> int:
        """Approximate chunk count for a section query via broad search.

        Used by the Layer 1 coverage audit to detect starved sections.
        """
        return len(self.search(run_id=run_id, query_text=query_text, k=k, min_credibility=0.0))

    # ------------------------------------------------------------------
    # Topic cache
    # ------------------------------------------------------------------

    def find_cached_run(self, query: str) -> str | None:
        """Return a cached run_id if a semantically similar query ran recently.

        Returns None when in-memory mode is active (no cross-run persistence).
        """
        if self._in_memory:
            return None

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
        """Index this run's query embedding so future runs can cache-hit it.

        No-op when in-memory mode is active.
        """
        if self._in_memory:
            return

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
        """Delete run collections whose cache entry is older than TTL.

        Should be called after each run completes to prevent unbounded
        collection growth in Qdrant.  Returns a list of deleted collection names.

        No-op when in-memory mode is active.
        """
        if self._in_memory:
            return []

        self.ensure_topic_cache_index()
        cutoff = datetime.now(timezone.utc) - timedelta(days=TOPIC_CACHE_TTL_DAYS)
        deleted: list[str] = []

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

        if deleted:
            logger.info("[VectorStore] Cleaned up %d expired collections.", len(deleted))
        return deleted
