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

CHUNKS_COLLECTION = "singularity_chunks"
PAYLOAD_INDEX_FIELDS = (
    "user_id",
    "workspace_id",
    "conversation_id",
    "project_id",
    "report_id",
    "document_id",
    "research_run_id",
    "visibility",
)

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
