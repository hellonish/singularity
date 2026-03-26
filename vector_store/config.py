# Qdrant collection configuration constants (moved from schema.py)
COLLECTION_CONFIG = {
    "size": 384,
    "distance": "Cosine",
}
TOPIC_CACHE_COLLECTION = "__topic_cache_index__"
TOPIC_CACHE_SIMILARITY_THRESHOLD = 0.92
TOPIC_CACHE_TTL_DAYS = 7
