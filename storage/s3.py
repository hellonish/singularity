from __future__ import annotations

import io
from typing import Any

import aioboto3

from api.config import settings


class S3BlobStore:
    """
    Production blob store backed by AWS S3 or any S3-compatible object store
    (Cloudflare R2, MinIO, etc.).

    Uses aioboto3 for async S3 operations.
    All content is stored with UTF-8 text encoding under the configured bucket.
    """

    def __init__(
        self,
        bucket: str | None = None,
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ) -> None:
        self._bucket = bucket or settings.s3_bucket
        self._endpoint_url = endpoint_url or settings.s3_endpoint_url or None
        self._access_key = aws_access_key_id or settings.aws_access_key_id or None
        self._secret_key = aws_secret_access_key or settings.aws_secret_access_key or None
        self._session = aioboto3.Session()

    def _client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        if self._access_key and self._secret_key:
            kwargs["aws_access_key_id"] = self._access_key
            kwargs["aws_secret_access_key"] = self._secret_key
        return kwargs

    async def write(self, key: str, content: str) -> str:
        encoded = content.encode("utf-8")
        async with self._session.client("s3", **self._client_kwargs()) as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=encoded,
                ContentType="text/plain; charset=utf-8",
            )
        return f"s3://{self._bucket}/{key}"

    async def read(self, key: str) -> str:
        async with self._session.client("s3", **self._client_kwargs()) as s3:
            try:
                response = await s3.get_object(Bucket=self._bucket, Key=key)
                body: bytes = await response["Body"].read()
                return body.decode("utf-8")
            except s3.exceptions.NoSuchKey:
                raise FileNotFoundError(f"S3 object not found: s3://{self._bucket}/{key}")

    async def exists(self, key: str) -> bool:
        async with self._session.client("s3", **self._client_kwargs()) as s3:
            try:
                await s3.head_object(Bucket=self._bucket, Key=key)
                return True
            except Exception:
                return False

    async def delete(self, key: str) -> None:
        async with self._session.client("s3", **self._client_kwargs()) as s3:
            await s3.delete_object(Bucket=self._bucket, Key=key)
