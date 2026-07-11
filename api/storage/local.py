from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from pathlib import Path, PurePosixPath

from api.storage.base import ObjectMetadata


class LocalObjectStore:
    """Atomic local filesystem implementation of the object-store contract."""

    scheme = "local"

    def __init__(self, root: str) -> None:
        self._root = Path(root).expanduser().resolve()

    @staticmethod
    def _normalise_key(key: str) -> str:
        path = PurePosixPath(key)
        if not key or path.is_absolute() or ".." in path.parts:
            raise ValueError("storage key must be a non-empty relative path")
        return path.as_posix()

    def _path_for_key(self, key: str) -> Path:
        safe_key = self._normalise_key(key)
        target = (self._root / safe_key).resolve()
        try:
            target.relative_to(self._root)
        except ValueError as exc:
            raise ValueError("storage key escapes local storage root") from exc
        return target

    def _key_from_uri(self, uri: str) -> str:
        prefix = f"{self.scheme}://"
        if not uri.startswith(prefix):
            raise ValueError(f"expected a {self.scheme} storage URI")
        return self._normalise_key(uri.removeprefix(prefix))

    async def put_bytes(self, key: str, data: bytes, *, content_type: str) -> ObjectMetadata:
        return await asyncio.to_thread(self._put_bytes_sync, key, data, content_type)

    def _put_bytes_sync(self, key: str, data: bytes, content_type: str) -> ObjectMetadata:
        target = self._path_for_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(prefix=".upload-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, target)
        except Exception:
            Path(temporary_path).unlink(missing_ok=True)
            raise

        return ObjectMetadata(
            uri=f"{self.scheme}://{self._normalise_key(key)}",
            key=self._normalise_key(key),
            size_bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
            content_type=content_type,
        )

    async def get_bytes(self, uri: str) -> bytes:
        path = self._path_for_key(self._key_from_uri(uri))
        return await asyncio.to_thread(path.read_bytes)

    async def exists(self, uri: str) -> bool:
        path = self._path_for_key(self._key_from_uri(uri))
        return await asyncio.to_thread(path.is_file)

    async def delete(self, uri: str) -> None:
        path = self._path_for_key(self._key_from_uri(uri))
        await asyncio.to_thread(path.unlink, missing_ok=True)
