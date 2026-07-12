"""Contracts shared by trusted research tools.

Tool implementations deliberately know nothing about skills, Modal, requests, or
application credentials.  They expose a small, declarative contract that the
application can register against one or more future skills.  This keeps the
same implementation usable locally today and from a Modal Function later.
"""
import asyncio
import ssl
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal


ExecutionKind = Literal["trusted_function", "sandbox", "api_only"]


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

    def __post_init__(self) -> None:
        # Clamp credibility_base to [0, 1] so downstream filtering logic
        # can rely on the invariant without guarding every comparison.
        self.credibility_base = max(0.0, min(1.0, self.credibility_base))

    @classmethod
    def failure(cls, error: str) -> "ToolResult":
        """Construct a failed result without raising."""
        return cls(content="", sources=[], credibility_base=0.0, error=error)

    @property
    def ok(self) -> bool:
        return self.error is None


class ToolBase:
    """Base class for deterministic, trusted tool implementations.

    ``name`` is the stable operation identifier used at the execution boundary.
    ``skill_ids`` are optional declarative defaults; a future skill can also be
    bound to a tool in :mod:`tools.registry` without changing either module.
    No skill module is imported here, preventing a tools-to-skills dependency.
    """

    name: str = "base"
    description: str = ""
    skill_ids: ClassVar[tuple[str, ...]] = ()
    execution_kind: ClassVar[ExecutionKind] = "trusted_function"

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
