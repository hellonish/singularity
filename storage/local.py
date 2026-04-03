from __future__ import annotations

import asyncio
from pathlib import Path


class LocalBlobStore:
    """
    Development blob store backed by the local filesystem.

    All blobs are written as UTF-8 text files under `base_dir`.
    Keys may include path separators (``/``) to create subdirectories.
    """

    def __init__(self, base_dir: str = "./blob_storage") -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Resolve within base_dir to prevent path traversal
        resolved = (self._base / key).resolve()
        if not str(resolved).startswith(str(self._base.resolve())):
            raise ValueError(f"Key {key!r} resolves outside base directory")
        return resolved

    async def write(self, key: str, content: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_text, content, encoding="utf-8")
        return f"local://{key}"

    async def read(self, key: str) -> str:
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(f"Blob not found: {key!r}")
        return await asyncio.to_thread(path.read_text, encoding="utf-8")

    async def exists(self, key: str) -> bool:
        return self._path(key).exists()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            await asyncio.to_thread(path.unlink)
