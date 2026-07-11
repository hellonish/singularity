from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_session
from api.models import User

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    x_user_id: Annotated[str, Header(alias="X-User-ID")],
) -> User:
    """Temporary development identity boundary.

    Replace this dependency with the rebuilt authentication flow without changing
    router/service signatures.
    """
    user = await session.get(User, x_user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown active user")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
