from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from arq import ArqRedis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from db.models import User
from db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/google", auto_error=False)

# Module-level ARQ Redis pool — initialised during app lifespan.
# ArqRedis extends redis.asyncio.Redis so pub/sub and all standard
# Redis commands are available alongside .enqueue_job().
_redis_pool: Optional[ArqRedis] = None


def set_redis_pool(pool: ArqRedis) -> None:
    global _redis_pool
    _redis_pool = pool


async def get_redis() -> AsyncGenerator[ArqRedis, None]:
    if _redis_pool is None:
        raise RuntimeError("Redis pool has not been initialised")
    yield _redis_pool


async def _decode_user_from_token(token: str, db: AsyncSession) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()
    if user is None:
        raise credentials_exc
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _decode_user_from_token(token, db)


async def get_current_user_optional(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        return await _decode_user_from_token(token, db)
    except HTTPException:
        return None
