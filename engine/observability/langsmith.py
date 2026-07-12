"""Fail-open LangSmith tracing for the local chat runtime.

The adapter intentionally uses LangSmith's standalone SDK, not LangChain.
"""
from __future__ import annotations

import hashlib
import logging
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)
_SECRET_PATTERN = __import__("re").compile(
    r"(?i)(api[_-]?key|apikey|token|authorization)(=|:|%3d)\s*([^&\s'\"]+)"
)


def _enabled() -> bool:
    return os.getenv("LANGSMITH_TRACING", "false").lower() in {"1", "true", "yes"} and bool(
        os.getenv("LANGSMITH_API_KEY")
    )


def _content_enabled() -> bool:
    return os.getenv("SINGULARITY_LANGSMITH_CAPTURE_CONTENT", "false").lower() in {"1", "true", "yes"}


def _digest(value: str) -> dict[str, Any]:
    return {"characters": len(value), "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest()}


@dataclass
class TraceSpan:
    """Small output API shared by real and disabled tracing spans."""

    run: Any | None = None

    def end(self, outputs: dict[str, Any]) -> None:
        if self.run is None:
            return
        try:
            self.run.end(outputs=outputs)
        except Exception:  # observability must not fail a chat turn
            logger.debug("LangSmith span output failed", exc_info=True)


class LangSmithTracer:
    """Creates nested, sanitized LangSmith spans when explicitly configured."""

    def __init__(self) -> None:
        self.enabled = _enabled()
        self.capture_content = _content_enabled()
        self.project_name = os.getenv("LANGSMITH_PROJECT", "singularity-dev")
        self._client: Any | None = None
        if self.enabled:
            try:
                from langsmith import Client

                # LangSmith batches traces in background threads. Transport
                # failures must not write SDK diagnostics over the interactive
                # prompt; Singularity remains fail-open and exposes whether
                # tracing is configured through /status.
                logging.getLogger("langsmith").setLevel(logging.CRITICAL)
                self._client = Client(
                    api_key=os.environ["LANGSMITH_API_KEY"],
                    api_url=os.getenv("LANGSMITH_ENDPOINT"),
                )
            except Exception:
                logger.warning("LangSmith is unavailable; continuing without tracing", exc_info=True)
                self.enabled = False

    def text(self, value: str) -> str | dict[str, Any]:
        sanitized = _SECRET_PATTERN.sub(r"\1\2[REDACTED]", value)
        return sanitized if self.capture_content else _digest(sanitized)

    @asynccontextmanager
    async def span(
        self,
        name: str,
        *,
        run_type: str = "chain",
        inputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> AsyncIterator[TraceSpan]:
        if not self.enabled or self._client is None:
            yield TraceSpan()
            return
        from langsmith.run_helpers import trace

        manager = trace(
                name,
                run_type=run_type,
                inputs=inputs,
                metadata=metadata,
                tags=tags,
                project_name=self.project_name,
                client=self._client,
            )
        try:
            run = await manager.__aenter__()
        except Exception:
            logger.debug("LangSmith span setup failed; continuing without it", exc_info=True)
            yield TraceSpan()
            return
        try:
            yield TraceSpan(run)
        except BaseException:
            await manager.__aexit__(*sys.exc_info())
            raise
        else:
            try:
                await manager.__aexit__(None, None, None)
            except Exception:
                logger.debug("LangSmith span finalization failed", exc_info=True)
