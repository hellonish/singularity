"""
Redis-backed sliding-window rate limiter middleware.

Uses a sorted-set per client key to track request timestamps.
Configurable via settings (or env vars):

    RATE_LIMIT_RPM=60          # requests per minute
    RATE_LIMIT_BURST=10        # burst allowance

Pinned to per-user limits when ``request.state.user_id`` is available
(post-auth), otherwise falls back to client IP.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from arq import ArqRedis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from api.config import settings

logger = logging.getLogger(__name__)

# How many requests allowed per sliding window (60 s by default).
_RATE_LIMIT_RPM: int = getattr(settings, "rate_limit_rpm", 60)
_WINDOW_SECONDS: int = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter backed by Redis sorted sets.

    Each client is identified by user_id (when authenticated) or
    source IP as a fallback.  The middleware maintains a sorted set
    of timestamps in Redis and trims entries older than the window
    before checking the count against the limit.

    If Redis is unreachable (timeout/connection errors), requests pass through
    without limiting so the API remains available; a warning is logged.
    """

    def __init__(self, app, redis_getter=None):
        super().__init__(app)
        # Allow injection of a redis getter for testing; production
        # reads from the global pool set in api.deps.
        self._get_redis = redis_getter

    async def _get_redis_pool(self) -> Optional[ArqRedis]:
        if self._get_redis:
            return await self._get_redis()
        # Lazy import to avoid circular references at module level
        from api.deps import _redis_pool
        return _redis_pool

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only rate-limit API routes
        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)

        redis: Optional[ArqRedis] = await self._get_redis_pool()
        if redis is None:
            # Redis not ready yet (e.g. during startup) — pass through
            return await call_next(request)

        client_key = self._client_key(request)
        now = time.time()
        window_start = now - _WINDOW_SECONDS
        key = f"ratelimit:{client_key}"

        pipe = redis.pipeline(transaction=True)
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current window entries
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Set TTL on the key to auto-clean
        pipe.expire(key, _WINDOW_SECONDS + 1)
        try:
            results = await pipe.execute()
        except (RedisTimeoutError, RedisConnectionError) as exc:
            # Redis down/slow would otherwise 500 every /api/v1 request; fail-open until Redis is healthy.
            logger.warning(
                "Rate limit skipped (Redis unreachable): %s client_key=%s",
                exc,
                client_key,
            )
            return await call_next(request)

        current_count: int = results[1]

        if current_count >= _RATE_LIMIT_RPM:
            logger.warning("Rate limit exceeded for %s (%d requests in window)", client_key, current_count)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down.",
                    "retry_after_seconds": _WINDOW_SECONDS,
                },
            )

        return await call_next(request)

    @staticmethod
    def _client_key(request: Request) -> str:
        """Use authenticated user_id when available, else IP."""
        user_id: str | None = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        forwarded = request.headers.get("X-Forwarded-For", "")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        return f"ip:{ip}"
