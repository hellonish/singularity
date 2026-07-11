from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    uri: str
    key: str
    size_bytes: int
    checksum_sha256: str
    content_type: str


class ObjectStore(Protocol):
    """Provider-neutral storage contract for local disk today and S3 later."""

    async def put_bytes(self, key: str, data: bytes, *, content_type: str) -> ObjectMetadata: ...

    async def get_bytes(self, uri: str) -> bytes: ...

    async def exists(self, uri: str) -> bool: ...

    async def delete(self, uri: str) -> None: ...
