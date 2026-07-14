from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

import aioboto3
from botocore.exceptions import ClientError

from api.storage.base import ObjectMetadata


class S3ObjectStore:
    """S3-compatible object store, used for Supabase Storage.

    Supabase exposes an S3-compatible endpoint, so this adapter works against
    real AWS S3 or Supabase interchangeably; only endpoint and credentials
    differ. URIs use an ``s3://<key>`` scheme (the bucket is fixed per store),
    matching the provider-neutral ``ObjectStore`` contract that callers depend
    on. A single ``aioboto3.Session`` is reused; a fresh client is opened per
    call because aioboto3 clients are async context managers.
    """

    scheme = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str | None = None,
        region_name: str = "us-east-1",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        if not bucket:
            raise ValueError("s3 storage requires a bucket name")
        self.bucket = bucket
        self._endpoint_url = endpoint_url
        self._region_name = region_name
        self._session = aioboto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
        )

    def _client(self):
        return self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            region_name=self._region_name,
        )

    @staticmethod
    def _normalise_key(key: str) -> str:
        path = PurePosixPath(key)
        if not key or path.is_absolute() or ".." in path.parts:
            raise ValueError("storage key must be a non-empty relative path")
        return path.as_posix()

    def _key_from_uri(self, uri: str) -> str:
        prefix = f"{self.scheme}://"
        if not uri.startswith(prefix):
            raise ValueError(f"expected a {self.scheme} storage URI")
        return self._normalise_key(uri.removeprefix(prefix))

    async def put_bytes(self, key: str, data: bytes, *, content_type: str) -> ObjectMetadata:
        safe_key = self._normalise_key(key)
        checksum = hashlib.sha256(data).hexdigest()
        async with self._client() as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=safe_key,
                Body=data,
                ContentType=content_type,
                Metadata={"sha256": checksum},
            )
        return ObjectMetadata(
            uri=f"{self.scheme}://{safe_key}",
            key=safe_key,
            size_bytes=len(data),
            checksum_sha256=checksum,
            content_type=content_type,
        )

    async def get_bytes(self, uri: str) -> bytes:
        key = self._key_from_uri(uri)
        async with self._client() as client:
            response = await client.get_object(Bucket=self.bucket, Key=key)
            async with response["Body"] as stream:
                return await stream.read()

    async def exists(self, uri: str) -> bool:
        key = self._key_from_uri(uri)
        async with self._client() as client:
            try:
                await client.head_object(Bucket=self.bucket, Key=key)
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                    return False
                raise
            return True

    async def delete(self, uri: str) -> None:
        key = self._key_from_uri(uri)
        async with self._client() as client:
            await client.delete_object(Bucket=self.bucket, Key=key)
