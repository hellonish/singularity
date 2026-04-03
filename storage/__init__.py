from __future__ import annotations

from api.config import settings
from storage.base import BlobStore
from storage.local import LocalBlobStore
from storage.s3 import S3BlobStore


def get_blob_store() -> BlobStore:
    """
    Return the configured BlobStore implementation.

    Reads ``settings.blob_store`` to decide which backend to instantiate:
    - ``"local"`` → :class:`LocalBlobStore` (development)
    - ``"s3"``    → :class:`S3BlobStore` (production / staging)
    """
    if settings.blob_store == "s3":
        return S3BlobStore()
    return LocalBlobStore(base_dir=settings.local_blob_dir)


__all__ = ["BlobStore", "LocalBlobStore", "S3BlobStore", "get_blob_store"]
