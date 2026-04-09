"""
JWT authentication middleware.

Validates Bearer tokens on every request to /api/v1/* (except
explicitly whitelisted paths like /auth/google).  Attaches the
decoded user_id to ``request.state`` so downstream dependencies
and the usage emitter can read it without re-decoding.
"""
from __future__ import annotations

import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from jose import JWTError, jwt

from api.config import settings

logger = logging.getLogger(__name__)

# Paths that do NOT require authentication.
_PUBLIC_PREFIXES = (
    "/api/v1/auth/google",
    "/api/v1/auth/refresh",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/health",
    "/api/ready",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Lightweight JWT guard that runs before route matching.

    For requests that carry a valid ``Authorization: Bearer <token>``
    header the ``sub`` claim is stored in ``request.state.user_id``.

    Requests to public endpoints bypass validation entirely.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip auth for public endpoints and non-API routes
        if not path.startswith("/api/v1/") or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        # SSE endpoints handle their own auth via query-param token
        if path.endswith("/events") or path.endswith("/messages"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Auth rejected for %s — missing/invalid Authorization header", path)
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except JWTError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        token_type = payload.get("type", "access")
        if token_type != "access":
            return JSONResponse(
                status_code=401,
                content={"detail": f"Expected access token, got {token_type}"},
            )

        user_id = payload.get("sub")
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token missing subject claim"},
            )

        # Attach for downstream use (deps.get_current_user still does full validation)
        request.state.user_id = user_id
        request.state.token_payload = payload

        return await call_next(request)
