"""At-most-once walkthrough claims backed by a unique constraint.

The database is the source of truth. A claim is an atomic
``INSERT ... ON CONFLICT DO NOTHING`` against ``user_walkthroughs``' composite
primary key: exactly one caller inserts the row and is authorized to display the
walkthrough; every concurrent tab, device, or duplicated request conflicts and
is told not to show it. No application-level lock is required — the unique
constraint handles concurrency.

Completion and dismissal are idempotent updates; both terminal states prevent
future display for that ``(user, key, version)``.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import UserWalkthrough


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def claim(
    session: AsyncSession, *, user_id: str, walkthrough_key: str, version: int
) -> bool:
    """Attempt to claim the walkthrough for this user; return whether to show it.

    ``True`` means this call inserted the row and the caller is the single
    authorized displayer. ``False`` means it was already claimed, completed, or
    dismissed.
    """
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    statement = (
        insert(UserWalkthrough)
        .values(
            user_id=user_id,
            walkthrough_key=walkthrough_key,
            version=version,
            status="claimed",
        )
        .on_conflict_do_nothing(
            index_elements=["user_id", "walkthrough_key", "version"]
        )
        .returning(UserWalkthrough.walkthrough_key)
    )
    result = await session.execute(statement)
    inserted = result.scalar_one_or_none() is not None
    await session.commit()
    return inserted


async def complete(
    session: AsyncSession, *, user_id: str, walkthrough_key: str, version: int
) -> None:
    """Mark a claimed walkthrough completed (idempotent)."""
    await _terminalize(
        session,
        user_id=user_id,
        walkthrough_key=walkthrough_key,
        version=version,
        status="completed",
        timestamp_column=UserWalkthrough.completed_at,
    )


async def dismiss(
    session: AsyncSession, *, user_id: str, walkthrough_key: str, version: int
) -> None:
    """Mark a claimed walkthrough dismissed (idempotent)."""
    await _terminalize(
        session,
        user_id=user_id,
        walkthrough_key=walkthrough_key,
        version=version,
        status="dismissed",
        timestamp_column=UserWalkthrough.dismissed_at,
    )


async def _terminalize(
    session: AsyncSession,
    *,
    user_id: str,
    walkthrough_key: str,
    version: int,
    status: str,
    timestamp_column,
) -> None:
    now = _now()
    # COALESCE keeps the first terminal timestamp so repeated calls are idempotent.
    statement = (
        update(UserWalkthrough)
        .where(
            UserWalkthrough.user_id == user_id,
            UserWalkthrough.walkthrough_key == walkthrough_key,
            UserWalkthrough.version == version,
        )
        .values(
            status=status,
            updated_at=now,
            **{timestamp_column.key: func.coalesce(timestamp_column, now)},
        )
    )
    await session.execute(statement)
    await session.commit()
