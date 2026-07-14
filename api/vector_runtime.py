from __future__ import annotations

from functools import lru_cache

from vector_store.client import VectorStoreClient


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStoreClient:
    """Return the process-wide vector store client.

    Mirrors ``api.storage.factory.get_object_store``: one shared client so
    report ingestion (research worker) and chat retrieval (request path) reuse
    the same connection. Connection details come from ``QDRANT_*`` environment
    variables read inside ``VectorStoreClient``.
    """
    return VectorStoreClient()
