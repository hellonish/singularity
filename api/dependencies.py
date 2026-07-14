from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import get_session
from api.models import User

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _user_from_bearer(session: AsyncSession, authorization: str | None) -> User:
    from api.services.auth import decode_access_token

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(authorization.split(" ", 1)[1].strip())
    user = await session.get(User, user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown active user")
    return user


async def _user_from_header(session: AsyncSession, x_user_id: str | None) -> User:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-User-ID")
    user = await session.get(User, x_user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown active user")
    return user


async def get_current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
) -> User:
    """Resolve the caller's identity.

    In the default ``bearer`` mode this verifies a signed access JWT issued by
    ``/auth/*``. The ``header`` mode preserves the temporary ``X-User-ID``
    boundary for local curl and the deterministic test suite. Both branches
    return the same ``User``, so router and service signatures never change.
    """
    if settings.auth_mode == "header":
        return await _user_from_header(session, x_user_id)
    return await _user_from_bearer(session, authorization)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
