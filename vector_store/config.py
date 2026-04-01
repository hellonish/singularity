"""Qdrant configuration constants for the vector store package."""
import os

# ---------------------------------------------------------------------------
# Embedding model settings
# ---------------------------------------------------------------------------

EMBEDDING_DIM = 384   # all-MiniLM-L6-v2 output dimension; must match the model in embedder.py

# ---------------------------------------------------------------------------
# Collection settings
# ---------------------------------------------------------------------------

COLLECTION_CONFIG = {
    "size": EMBEDDING_DIM,
    "distance": "Cosine",
}

# ---------------------------------------------------------------------------
# Topic cache
# ---------------------------------------------------------------------------

TOPIC_CACHE_COLLECTION       = "__topic_cache_index__"
TOPIC_CACHE_SIMILARITY_THRESHOLD = 0.92
TOPIC_CACHE_TTL_DAYS         = 7

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

QDRANT_CONNECT_TIMEOUT = int(os.getenv("QDRANT_CONNECT_TIMEOUT", "3"))  # seconds

# Set QDRANT_FORCE_IN_MEMORY=1 to always use in-memory mode (e.g. in tests
# or CI where no Qdrant server is available). When unset, the client
# connects to the configured server and raises loudly if it is unreachable.
FORCE_IN_MEMORY = os.getenv("QDRANT_FORCE_IN_MEMORY", "0") == "1"

# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

UPSERT_BATCH_SIZE = 64   # points per upsert call; keep below Qdrant's default request limit
