from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import jwt
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.schemas import TokenPair
from api.config import settings
from db.models import RefreshToken, User


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_aware(dt: datetime) -> datetime:
    """
    Normalize ORM-loaded datetimes for comparison.

    Some drivers return naive timestamps even for TIMESTAMPTZ columns; _now() is
    always UTC-aware, so comparisons must use the same awareness.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Google ID token verification
# ---------------------------------------------------------------------------


def verify_google_id_token(id_token: str) -> dict:
    """
    Verify a Google ID token and return the decoded payload.

    Returns a dict with at minimum: sub, email, name, picture.
    Raises HTTP 401 if verification fails.
    """
    try:
        request = google_requests.Request()
        payload = google_id_token.verify_oauth2_token(
            id_token,
            request,
            settings.google_client_id,
        )
    except (GoogleAuthError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {exc}",
        ) from exc

    return payload


# ---------------------------------------------------------------------------
# User upsert
# ---------------------------------------------------------------------------


async def upsert_user(db: AsyncSession, google_payload: dict) -> User:
    """
    Insert or update the user record based on the Google sub.

    On conflict (google_sub already exists) we update last_login_at, name,
    and avatar_url to keep profile info fresh.
    """
    sub: str = google_payload["sub"]
    email: str = google_payload["email"]
    name: str | None = google_payload.get("name")
    avatar_url: str | None = google_payload.get("picture")
    now = _now()

    stmt = (
        pg_insert(User)
        .values(
            id=uuid.uuid4(),
            google_sub=sub,
            email=email,
            name=name,
            avatar_url=avatar_url,
            created_at=now,
            last_login_at=now,
            daily_token_budget=settings.default_daily_token_budget,
            is_active=True,
        )
        .on_conflict_do_update(
            index_elements=["google_sub"],
            set_={
                "last_login_at": now,
                "name": name,
                "avatar_url": avatar_url,
            },
        )
        .returning(User)
    )

    result = await db.execute(stmt)
    await db.commit()
    user = result.scalar_one()
    return user


# ---------------------------------------------------------------------------
# Token issuance
# ---------------------------------------------------------------------------


def _build_access_token(user_id: str) -> str:
    expire = _now() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": _now(),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def create_token_pair(db: AsyncSession, user_id: uuid.UUID) -> TokenPair:
    """
    Issue a new JWT access token and an opaque refresh token.

    The refresh token is stored as a SHA-256 hash in refresh_tokens,
    assigned to a new rotation family.
    """
    access_token = _build_access_token(str(user_id))
    raw_refresh = secrets.token_urlsafe(48)
    family_id = uuid.uuid4()
    now = _now()
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)

    refresh_row = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw_refresh),
        family_id=family_id,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(refresh_row)
    await db.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ---------------------------------------------------------------------------
# Refresh token rotation
# ---------------------------------------------------------------------------


async def verify_refresh_token(db: AsyncSession, raw_token: str) -> tuple[User, TokenPair]:
    """
    Validate the raw refresh token, rotate it (issue new pair + revoke old),
    and return the authenticated user and new token pair.

    If the token has already been used (reuse detection), revoke the entire
    family to force re-authentication.
    """
    token_hash = _hash_token(raw_token)
    now = _now()

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt: RefreshToken | None = result.scalar_one_or_none()

    if rt is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    if rt.revoked_at is not None:
        # Token reuse detected — revoke entire family
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == rt.family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token already used — please log in again",
        )

    expires_at = _as_utc_aware(rt.expires_at)
    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    # Revoke the consumed token
    rt.revoked_at = now
    await db.flush()

    # Load user
    user_result = await db.execute(select(User).where(User.id == rt.user_id))
    user: User | None = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Issue new pair in the same family
    access_token = _build_access_token(str(user.id))
    raw_refresh_new = secrets.token_urlsafe(48)
    new_expires_at = now + timedelta(days=settings.refresh_token_expire_days)

    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_refresh_new),
        family_id=rt.family_id,
        created_at=now,
        expires_at=new_expires_at,
    )
    db.add(new_rt)
    await db.commit()

    return user, TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh_new,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    """Mark a refresh token as revoked."""
    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    rt: RefreshToken | None = result.scalar_one_or_none()
    if rt is not None:
        rt.revoked_at = _now()
        await db.commit()


# ---------------------------------------------------------------------------
# Short-lived SSE token
# ---------------------------------------------------------------------------


def create_sse_token(user_id: uuid.UUID) -> str:
    """
    Issue a 30-second single-use token for SSE endpoint authentication.

    The token is a compact JWT with type="sse" and a very short expiry.
    """
    expire = _now() + timedelta(seconds=30)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": _now(),
        "type": "sse",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
