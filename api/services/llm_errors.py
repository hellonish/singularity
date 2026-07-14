"""Shared mapping from engine provider failures to stable HTTP errors.

Both the request-scoped completion route and the streaming chat endpoint use
this so a single policy governs status codes, retry semantics, and the
`Retry-After` passthrough. A provider API key or raw upstream error body is
never exposed by the returned error.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from engine.llm.groq import GroqProviderError


def provider_error(exc: GroqProviderError) -> HTTPException:
    headers = {"Retry-After": exc.retry_after_seconds} if exc.retry_after_seconds else None
    http_status = (
        status.HTTP_429_TOO_MANY_REQUESTS
        if exc.code == "provider_rate_limited"
        else status.HTTP_503_SERVICE_UNAVAILABLE
        if exc.retryable
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable},
        headers=headers,
    )
