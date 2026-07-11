"""Small, dependency-free per-user rate limiting for write endpoints.

This implementation is intentionally process-local for the SQLite/local API
foundation. Replace its event store with Redis before running multiple API
processes, since each process otherwise has an independent limit.
"""
from __future__ import annotations

import asyncio
import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from fastapi import Request
from fastapi.responses import JSONResponse, Response

RateLimitAction = Literal["message", "chat", "report"]


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: float = 0.0


class PerUserSlidingWindowLimiter:
    """A concurrency-safe sliding-window limiter keyed by (user, action)."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._events: dict[tuple[str, RateLimitAction], deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, user_id: str, action: RateLimitAction, limit: int) -> RateLimitResult:
        now = self._clock()
        key = (user_id, action)
        async with self._lock:
            events = self._events[key]
            window_start = now - 1.0
            while events and events[0] <= window_start:
                events.popleft()

            if len(events) >= limit:
                return RateLimitResult(allowed=False, retry_after_seconds=events[0] + 1.0 - now)

            events.append(now)
            return RateLimitResult(allowed=True)


def action_for_request(request: Request) -> RateLimitAction | None:
    """Return the one write action limited by this request, if any."""

    if request.method != "POST":
        return None

    path = request.url.path.rstrip("/") or "/"
    if path == "/chats":
        return "chat"
    if path == "/reports":
        return "report"

    chat_segments = path.split("/")
    if (
        len(chat_segments) in {4, 5}
        and chat_segments[1] == "chats"
        and chat_segments[3] == "messages"
        and (len(chat_segments) == 4 or chat_segments[4] == "stream")
    ):
        return "message"
    return None


class ChatReportRateLimitMiddleware:
    """Enforce the chat/message/report creation limits for an identified user."""

    def __init__(
        self,
        app,
        *,
        messages_per_second: int,
        chats_per_second: int,
        reports_per_second: int,
    ) -> None:
        self.app = app
        self._limiter = PerUserSlidingWindowLimiter()
        self._limits: dict[RateLimitAction, int] = {
            "message": messages_per_second,
            "chat": chats_per_second,
            "report": reports_per_second,
        }

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        action = action_for_request(request)
        user_id = request.headers.get("x-user-id")
        if action is None or not user_id:
            await self.app(scope, receive, send)
            return

        result = await self._limiter.check(user_id, action, self._limits[action])
        if result.allowed:
            await self.app(scope, receive, send)
            return

        retry_after = max(1, math.ceil(result.retry_after_seconds))
        response = JSONResponse(
            status_code=429,
            content={
                "detail": f"Rate limit exceeded: {self._limits[action]} {action} requests per second",
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(self._limits[action]),
            },
        )
        await response(scope, receive, send)
