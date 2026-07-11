from __future__ import annotations

from api.storage.base import ObjectMetadata


class S3ObjectStore:
    """Supabase S3 adapter template.

    Implement this class with the Supabase S3 client later; callers already
    depend only on the provider-neutral ObjectStore contract.
    """

    def __init__(self, *, bucket: str) -> None:
        self.bucket = bucket

    async def put_bytes(self, key: str, data: bytes, *, content_type: str) -> ObjectMetadata:
        raise NotImplementedError("Configure the Supabase S3 adapter before using the s3 backend")

    async def get_bytes(self, uri: str) -> bytes:
        raise NotImplementedError("Configure the Supabase S3 adapter before using the s3 backend")

    async def exists(self, uri: str) -> bool:
        raise NotImplementedError("Configure the Supabase S3 adapter before using the s3 backend")

    async def delete(self, uri: str) -> None:
        raise NotImplementedError("Configure the Supabase S3 adapter before using the s3 backend")
