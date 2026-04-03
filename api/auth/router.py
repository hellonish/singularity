from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.schemas import GoogleAuthRequest, RefreshRequest, TokenPair
from api.auth.service import (
    create_sse_token,
    create_token_pair,
    revoke_refresh_token,
    upsert_user,
    verify_google_id_token,
    verify_refresh_token,
)
from api.deps import get_current_user, get_db
from db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def google_auth(
    body: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """
    Exchange a Google ID token for a Singularity JWT pair.

    The Google token is verified server-side, the user row is upserted,
    and a fresh access + refresh token pair is returned.
    """
    google_payload = verify_google_id_token(body.id_token)
    user = await upsert_user(db, google_payload)
    return await create_token_pair(db, user.id)


@router.post("/refresh", response_model=TokenPair, status_code=status.HTTP_200_OK)
async def refresh_tokens(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """
    Rotate a refresh token.

    The supplied token is revoked and a new pair is issued.  If the token has
    already been used (replay attack), the entire rotation family is revoked.
    """
    _user, token_pair = await verify_refresh_token(db, body.refresh_token)
    return token_pair


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    body: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke the supplied refresh token (effectively logging out the session)."""
    await revoke_refresh_token(db, body.refresh_token)
    return {"status": "logged_out"}


@router.get("/sse-token", status_code=status.HTTP_200_OK)
async def get_sse_token(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Issue a short-lived (30 s) token for SSE endpoint authentication.

    Clients that cannot attach an Authorization header (e.g. EventSource)
    should call this first and pass the returned token as a query parameter.
    """
    token = create_sse_token(current_user.id)
    return {"token": token, "expires_in": 30}
