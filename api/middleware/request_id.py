"""
Request ID middleware.

Generates a unique ID for every inbound request, attaches it to
``request.state.request_id``, and echoes it back in the response as
``X-Request-ID``.  When the caller supplies ``X-Request-ID`` it is
honoured (useful for tracing across service boundaries).

The ID is also injected into the log context via a ``logging.Filter`` so
every log record produced during the request lifecycle carries
``request_id`` without callers needing to pass it explicitly.
"""
from __future__ import annotations

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# contextvars-based store so the filter can read it without a reference to the request.
from contextvars import ContextVar

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the current request ID, or '-' outside a request context."""
    return _request_id_ctx.get()


class RequestIdFilter(logging.Filter):
    """Inject request_id into every LogRecord produced in this request context."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()  # type: ignore[attr-defined]
        return True


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Attach a unique request ID to every request.

    Priority:
    1. Use X-Request-ID header from the caller if present and non-empty.
    2. Generate a new UUID4 otherwise.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        token = _request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response
