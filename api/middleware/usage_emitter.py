from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Optional

import user_agents
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from api.db.models import UsageEvent
from api.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


def _parse_user_agent(ua_string: str) -> tuple[str, str, str]:
    """
    Parse a User-Agent string using the user_agents library.

    Returns (device_type, os, browser).
    """
    if not ua_string:
        return "unknown", "unknown", "unknown"

    ua = user_agents.parse(ua_string)

    if ua.is_mobile:
        device_type = "mobile"
    elif ua.is_tablet:
        device_type = "tablet"
    else:
        device_type = "desktop"

    os_name = ua.os.family or "unknown"
    browser_name = ua.browser.family or "unknown"

    return device_type, os_name, browser_name


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def _extract_user_id(request: Request) -> Optional[uuid.UUID]:
    """Attempt to read the authenticated user ID from request state."""
    user = getattr(request.state, "user", None)
    if user is not None:
        return getattr(user, "id", None)
    return None


async def _emit_usage_event(
    user_id: Optional[uuid.UUID],
    event_type: str,
    route: Optional[str],
    duration_ms: int,
    success: bool,
    status_code: int,
    ua_string: str,
    ip_address: str,
) -> None:
    """
    Persist a UsageEvent row in its own short-lived session.

    This runs as a fire-and-forget task — failures are logged but never
    propagate to the request/response cycle.
    """
    if user_id is None:
        return

    device_type, os_name, browser = _parse_user_agent(ua_string)
    error_code = str(status_code) if not success else None

    try:
        async with AsyncSessionLocal() as session:
            event = UsageEvent(
                user_id=user_id,
                event_type=event_type,
                route=route,
                duration_ms=duration_ms,
                success=success,
                error_code=error_code,
                user_agent=ua_string or None,
                ip_address=ip_address or None,
                device_type=device_type,
                os=os_name,
                browser=browser,
            )
            session.add(event)
            await session.commit()
    except Exception:
        logger.exception("Failed to emit usage event for user %s", user_id)


class UsageEmitterMiddleware(BaseHTTPMiddleware):
    """
    After every response, fire-and-forget a UsageEvent record.

    The task is scheduled with asyncio.create_task so it never delays
    the response reaching the client.
    """

    # Routes to skip tracking (e.g. health / readiness probes)
    _SKIP_PATHS = {"/api/health", "/api/ready", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        start_ms = time.monotonic()
        response: Response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start_ms) * 1000)

        user_id = _extract_user_id(request)
        ua_string = request.headers.get("User-Agent", "")
        ip_address = _get_client_ip(request)
        route = f"{request.method} {request.url.path}"
        success = response.status_code < 400

        # Classify event_type from path
        path = request.url.path
        if "/research/jobs" in path:
            event_type = "research_job"
        elif "/threads" in path:
            event_type = "chat_message"
        elif "/reports" in path:
            if "/patch" in path:
                event_type = "patch"
            else:
                event_type = "report_view"
        elif "/auth" in path:
            event_type = "auth"
        else:
            event_type = "api_request"

        asyncio.create_task(
            _emit_usage_event(
                user_id=user_id,
                event_type=event_type,
                route=route,
                duration_ms=elapsed_ms,
                success=success,
                status_code=response.status_code,
                ua_string=ua_string,
                ip_address=ip_address,
            )
        )

        return response
