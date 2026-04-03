"""
Gate for integration-test mock research (no LLM / pipeline).

Requires a master switch (DEBUG_MOCK_RESEARCH=true, or ENVIRONMENT=development)
and an allowlisted account email (DEBUG_MOCK_RESEARCH_ALLOW_EMAIL).
"""
from __future__ import annotations

from fastapi import HTTPException, status

from api.config import settings
from db.models import User

DEFAULT_ALLOW_EMAIL = "nish2002.sharma@gmail.com"


def _normalized_allow_email() -> str:
    raw = (settings.debug_mock_research_allow_email or DEFAULT_ALLOW_EMAIL).strip()
    return raw.lower()


def _debug_mock_master_enabled() -> bool:
    """
    True when the API may honor client debug_mock flags (allowlisted user still required).

    In development, mock is allowed without DEBUG_MOCK_RESEARCH in .env so local dashboards
    match the debug UI checkbox. Production should set ENVIRONMENT=production.
    """
    if settings.debug_mock_research:
        return True
    return (settings.environment or "").strip().lower() == "development"


def debug_mock_eligible_user(user: User) -> bool:
    """True if this user's email may use debug mock when the master switch is on."""
    if not _debug_mock_master_enabled():
        return False
    email = (user.email or "").strip().lower()
    return bool(email) and email == _normalized_allow_email()


def assert_debug_mock_request_allowed(user: User, debug_mock: bool) -> None:
    """
    If the client asks for debug_mock, require master switch + allowlisted email.
    Raises 403 when debug_mock is true but not permitted.
    """
    if not debug_mock:
        return
    if not _debug_mock_master_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Debug mock research is disabled on this server. "
                "Set DEBUG_MOCK_RESEARCH=true in the API .env, or set ENVIRONMENT=development."
            ),
        )
    email = (user.email or "").strip().lower()
    allow = _normalized_allow_email()
    if not email or email != allow:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Debug mock is not allowed for this account. "
                "Set DEBUG_MOCK_RESEARCH_ALLOW_EMAIL in the API .env to your Google login email "
                f"(currently allowlisted: {allow})."
            ),
        )


def use_debug_mock_research_job(user: User, debug_mock: bool) -> bool:
    """True when the dashboard job should run the mock worker instead of the real pipeline."""
    if not debug_mock:
        return False
    assert_debug_mock_request_allowed(user, debug_mock)
    return True
