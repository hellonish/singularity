"""
ToolBase and ToolResult — the foundation every tool is built on.

Every tool:
  - Subclasses ToolBase and sets `name`.
  - Implements async `call(query, **kwargs) -> ToolResult`.
  - Gets `call_with_retry` for free (exponential back-off, never raises).
"""
import asyncio
import ssl
from dataclasses import dataclass, field
from typing import Any


def ssl_ctx() -> ssl.SSLContext:
    """Return an SSL context with certifi's CA bundle (fixes macOS Python cert issues)."""
    import certifi
    return ssl.create_default_context(cafile=certifi.where())


@dataclass
class ToolResult:
    content: str             # primary extracted text / summary
    sources: list[dict]      # [{title, url, date, snippet, credibility_base, ...}]
    credibility_base: float  # 0-1 baseline before skill-level adjustments
    raw: Any = None          # raw API/library response (for debugging)
    error: str | None = None # set on failure; call_with_retry never raises

    @classmethod
    def failure(cls, error: str) -> "ToolResult":
        """Construct a failed result without raising."""
        return cls(content="", sources=[], credibility_base=0.0, error=error)

    @property
    def ok(self) -> bool:
        return self.error is None


class ToolBase:
    name: str = "base"

    async def call(self, query: str, **kwargs) -> ToolResult:
        """Single attempt — raises on error. Override this."""
        raise NotImplementedError

    async def call_with_retry(
        self,
        query: str,
        max_retries: int = 2,
        timeout: float = 60.0,
        **kwargs,
    ) -> ToolResult:
        """
        Retries call() with exponential back-off (1s, 2s, ...).
        Never raises — returns ToolResult.failure() after exhausting retries.
        Each attempt is bounded by `timeout` seconds (default 60s).
        """
        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                return await asyncio.wait_for(
                    self.call(query, **kwargs),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                last_error = f"timed out after {timeout}s"
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
            except Exception as exc:
                last_error = str(exc)
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)

        return ToolResult.failure(
            f"[{self.name}] failed after {max_retries + 1} attempt(s): {last_error}"
        )
