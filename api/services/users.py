from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import UsageAccount, User
from api.schemas import UserCreate, UserUpdate


async def create_user(session: AsyncSession, body: UserCreate) -> User:
    user = User(
        email=body.email,
        display_name=body.display_name,
        auth_provider=body.auth_provider,
        external_subject=body.external_subject,
    )
    session.add(user)
    await session.flush()
    session.add(UsageAccount(user_id=user.id))
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(session: AsyncSession, user: User, body: UserUpdate) -> User:
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.status is not None:
        user.status = body.status
    if body.profile_data is not None:
        user.profile_data = body.profile_data
    await session.commit()
    await session.refresh(user)
    return user


async def get_user(session: AsyncSession, user_id: str) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def deactivate_user(session: AsyncSession, user: User) -> None:
    """Soft-delete a user so their historical records remain available to admins."""

    user.status = "deleted"
    await session.commit()
