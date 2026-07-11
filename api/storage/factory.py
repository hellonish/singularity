from __future__ import annotations

from functools import lru_cache

from api.config import settings
from api.storage.local import LocalObjectStore


@lru_cache(maxsize=1)
def get_object_store() -> LocalObjectStore:
    if settings.storage_backend != "local":
        raise RuntimeError("Only the local storage backend is configured in API v2")
    return LocalObjectStore(settings.storage_root)
