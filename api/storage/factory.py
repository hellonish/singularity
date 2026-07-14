from __future__ import annotations

from functools import lru_cache

from api.config import settings
from api.storage.base import ObjectStore
from api.storage.local import LocalObjectStore
from api.storage.s3 import S3ObjectStore


@lru_cache(maxsize=1)
def get_object_store() -> ObjectStore:
    backend = settings.storage_backend
    if backend == "local":
        return LocalObjectStore(settings.storage_root)
    if backend == "s3":
        return S3ObjectStore(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
        )
    raise RuntimeError(f"Unknown storage backend: {backend!r} (expected 'local' or 's3')")
