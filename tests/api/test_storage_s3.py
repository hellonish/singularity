from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager

import pytest
from botocore.exceptions import ClientError

from api.storage.s3 import S3ObjectStore


class _FakeStream:
    def __init__(self, data: bytes) -> None:
        self._data = data

    async def __aenter__(self) -> "_FakeStream":
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def read(self) -> bytes:
        return self._data


class _FakeS3Client:
    """Minimal in-memory stand-in for the aioboto3 S3 client."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    async def __aenter__(self) -> "_FakeS3Client":
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def put_object(self, *, Bucket, Key, Body, ContentType, Metadata):
        self.objects[(Bucket, Key)] = Body

    async def get_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": _FakeStream(self.objects[(Bucket, Key)])}

    async def head_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {}

    async def delete_object(self, *, Bucket, Key):
        self.objects.pop((Bucket, Key), None)


@pytest.fixture()
def store(monkeypatch) -> S3ObjectStore:
    s = S3ObjectStore(
        bucket="reports",
        endpoint_url="https://proj.supabase.co/storage/v1/s3",
        region_name="us-east-1",
        access_key_id="key",
        secret_access_key="secret",
    )
    fake = _FakeS3Client()

    def _client():
        return fake

    monkeypatch.setattr(s, "_client", _client)
    return s


@pytest.mark.asyncio
async def test_put_get_round_trip(store: S3ObjectStore) -> None:
    data = b"# report body"
    meta = await store.put_bytes("reports/a.md", data, content_type="text/markdown")

    assert meta.uri == "s3://reports/a.md"
    assert meta.key == "reports/a.md"
    assert meta.size_bytes == len(data)
    assert meta.checksum_sha256 == hashlib.sha256(data).hexdigest()
    assert meta.content_type == "text/markdown"

    assert await store.get_bytes(meta.uri) == data


@pytest.mark.asyncio
async def test_exists_and_delete(store: S3ObjectStore) -> None:
    await store.put_bytes("reports/b.md", b"x", content_type="text/plain")
    uri = "s3://reports/b.md"

    assert await store.exists(uri) is True
    await store.delete(uri)
    assert await store.exists(uri) is False


@pytest.mark.asyncio
async def test_get_missing_key_raises(store: S3ObjectStore) -> None:
    with pytest.raises(ClientError):
        await store.get_bytes("s3://reports/missing.md")


def test_rejects_unsafe_keys() -> None:
    store = S3ObjectStore(bucket="b")
    for bad in ["", "/abs.md", "../escape.md"]:
        with pytest.raises(ValueError):
            store._normalise_key(bad)


def test_rejects_foreign_uri_scheme() -> None:
    store = S3ObjectStore(bucket="b")
    with pytest.raises(ValueError):
        store._key_from_uri("local://reports/a.md")


def test_requires_bucket() -> None:
    with pytest.raises(ValueError):
        S3ObjectStore(bucket="")


def test_factory_selects_s3(monkeypatch) -> None:
    from api.config import settings
    from api.storage import factory

    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", "reports")
    monkeypatch.setattr(settings, "s3_endpoint_url", "https://proj.supabase.co/storage/v1/s3")
    factory.get_object_store.cache_clear()
    try:
        store = factory.get_object_store()
        assert isinstance(store, S3ObjectStore)
        assert store.bucket == "reports"
    finally:
        factory.get_object_store.cache_clear()
