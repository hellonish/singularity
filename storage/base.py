from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BlobStore(Protocol):
    """
    Minimal async blob storage interface.

    Implementations must support write and read operations for
    UTF-8 text content keyed by an arbitrary string path/key.
    """

    async def write(self, key: str, content: str) -> str:
        """
        Persist text content under the given key.

        Returns the canonical URI/path by which the content can later be read.
        """
        ...

    async def read(self, key: str) -> str:
        """
        Retrieve text content stored at the given key.

        Raises FileNotFoundError if the key does not exist.
        """
        ...

    async def exists(self, key: str) -> bool:
        """Return True if the key exists in the store."""
        ...

    async def delete(self, key: str) -> None:
        """Remove the content at the given key.  No-op if not found."""
        ...
