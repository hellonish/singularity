"""
Thread service layer.

Manages conversation threads (both standalone chat and report-linked Q&A),
message persistence, and context assembly for the chat agent.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.reports.service import get_report, get_version_content, load_content
from api.db.models import Message, Report, Thread, User


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_thread(
    db: AsyncSession,
    user_id: uuid.UUID,
    report_id: Optional[uuid.UUID],
    pinned_version: Optional[int],
) -> Thread:
    """
    Create a new chat thread, optionally linked to a report.
    """
    if report_id:
        await get_report(db, report_id, user_id)

    thread = Thread(
        user_id=user_id,
        report_id=report_id,
        pinned_version_num=pinned_version,
        canonical_report_qa=False,
        created_at=_now(),
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


async def get_thread(
    db: AsyncSession,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Thread:
    """Fetch a thread with ownership check."""
    result = await db.execute(
        select(Thread).where(Thread.id == thread_id, Thread.user_id == user_id)
    )
    thread: Thread | None = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread


async def list_threads(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 20,
) -> list[Thread]:
    """List user's threads, newest first (created_at only — prefer list_threads_with_meta for UI)."""
    result = await db.execute(
        select(Thread)
        .where(Thread.user_id == user_id)
        .order_by(Thread.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_or_create_default_report_thread(
    db: AsyncSession,
    user_id: uuid.UUID,
    report_id: uuid.UUID,
) -> Thread:
    """
    Return the single canonical Q&A thread for this report, creating it if absent.

    Concurrent creates resolve via unique index + IntegrityError retry.
    """
    await get_report(db, report_id, user_id)
    result = await db.execute(
        select(Thread).where(
            Thread.user_id == user_id,
            Thread.report_id == report_id,
            Thread.canonical_report_qa.is_(True),
        )
    )
    existing: Thread | None = result.scalar_one_or_none()
    if existing is not None:
        return existing

    thread = Thread(
        user_id=user_id,
        report_id=report_id,
        pinned_version_num=None,
        canonical_report_qa=True,
        created_at=_now(),
    )
    db.add(thread)
    try:
        await db.commit()
        await db.refresh(thread)
        return thread
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(Thread).where(
                Thread.user_id == user_id,
                Thread.report_id == report_id,
                Thread.canonical_report_qa.is_(True),
            )
        )
        retry = result.scalar_one_or_none()
        if retry is None:
            raise
        return retry


async def list_threads_with_meta(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
) -> list[
    tuple[
        Thread,
        Optional[str],
        Optional[str],
        Optional[datetime],
        Optional[str],
        Optional[str],
    ]
]:
    """
    List threads with report title/query and message previews, ordered by last activity.

    At most one row per report: prefers ``canonical_report_qa`` then latest activity
    (avoids duplicate sidebar rows from legacy extra threads per report).

    Returns tuples:
    (thread, report_title, last_message_preview, last_message_at, report_query,
    first_user_message_preview).
    """
    last_at_sub = (
        select(
            Message.thread_id.label("tid"),
            func.max(Message.created_at).label("last_at"),
        )
        .group_by(Message.thread_id)
        .subquery()
    )

    sort_key_expr = func.coalesce(last_at_sub.c.last_at, Thread.created_at)
    ranked_sq = (
        select(
            Thread.id.label("picked_thread_id"),
            sort_key_expr.label("sort_key"),
            func.row_number()
            .over(
                partition_by=func.coalesce(Thread.report_id, Thread.id),
                order_by=(
                    Thread.canonical_report_qa.desc(),
                    sort_key_expr.desc(),
                ),
            )
            .label("rn"),
        )
        .select_from(Thread)
        .outerjoin(last_at_sub, Thread.id == last_at_sub.c.tid)
        .where(Thread.user_id == user_id)
    ).subquery()

    stmt = (
        select(Thread, Report.title, last_at_sub.c.last_at, Report.query)
        .join(ranked_sq, Thread.id == ranked_sq.c.picked_thread_id)
        .outerjoin(Report, Thread.report_id == Report.id)
        .outerjoin(last_at_sub, Thread.id == last_at_sub.c.tid)
        .where(ranked_sq.c.rn == 1)
        .order_by(ranked_sq.c.sort_key.desc())
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).all())
    thread_ids = [row[0].id for row in rows]
    preview_by_tid: dict[uuid.UUID, str] = {}
    first_user_by_tid: dict[uuid.UUID, str] = {}
    if thread_ids:
        rn = func.row_number().over(
            partition_by=Message.thread_id,
            order_by=Message.created_at.desc(),
        ).label("rn")
        ranked = (
            select(Message.thread_id, Message.content, rn)
            .where(Message.thread_id.in_(thread_ids))
            .subquery()
        )
        prev_stmt = select(ranked.c.thread_id, ranked.c.content).where(ranked.c.rn == 1)
        for tid, content in (await db.execute(prev_stmt)).all():
            text = (content or "").strip().replace("\n", " ")
            preview_by_tid[tid] = text[:120] + ("…" if len(text) > 120 else "")

        rn_first = func.row_number().over(
            partition_by=Message.thread_id,
            order_by=Message.created_at.asc(),
        ).label("rn_asc")
        ranked_first = (
            select(Message.thread_id, Message.content, rn_first)
            .where(
                Message.thread_id.in_(thread_ids),
                Message.role == "user",
            )
            .subquery()
        )
        first_stmt = select(ranked_first.c.thread_id, ranked_first.c.content).where(
            ranked_first.c.rn_asc == 1
        )
        for tid, content in (await db.execute(first_stmt)).all():
            text = (content or "").strip().replace("\n", " ")
            first_user_by_tid[tid] = text[:120] + ("…" if len(text) > 120 else "")

    out: list[
        tuple[
            Thread,
            Optional[str],
            Optional[str],
            Optional[datetime],
            Optional[str],
            Optional[str],
        ]
    ] = []
    for thread, title, last_at, report_query in rows:
        preview = preview_by_tid.get(thread.id)
        first_user = first_user_by_tid.get(thread.id)
        out.append((thread, title, preview, last_at, report_query, first_user))
    return out


async def update_thread_pin(
    db: AsyncSession,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
    pinned_version_num: Optional[int],
) -> Thread:
    """Set pinned report version for a thread (None = follow latest)."""
    thread = await get_thread(db, thread_id, user_id)
    thread.pinned_version_num = pinned_version_num
    await db.commit()
    await db.refresh(thread)
    return thread


async def save_message(
    db: AsyncSession,
    thread_id: uuid.UUID,
    role: str,
    content: str,
    token_count: Optional[int] = None,
) -> Message:
    """Persist a chat message."""
    message = Message(
        thread_id=thread_id,
        role=role,
        content=content,
        token_count=token_count,
        created_at=_now(),
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_messages(
    db: AsyncSession,
    thread_id: uuid.UUID,
    limit: int = 100,
) -> list[Message]:
    """Get messages for a thread, oldest first."""
    result = await db.execute(
        select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def assemble_context(
    db: AsyncSession,
    thread: Thread,
) -> tuple[list[dict], Optional[str]]:
    """
    Build the conversation context for the chat agent.

    Returns:
        - messages: list of {"role": ..., "content": ...} for the agent
        - report_md: the report markdown if linked, else None
    """
    # Load message history
    db_messages = await get_messages(db, thread.id)
    messages = [
        {"role": m.role, "content": m.content}
        for m in db_messages
    ]

    # Load linked report content if available
    report_md: Optional[str] = None
    if thread.report_id:
        version_num = thread.pinned_version_num
        if version_num:
            try:
                version = await get_version_content(
                    db, thread.report_id, version_num, thread.user_id,
                )
                report_md = await load_content(version)
            except HTTPException:
                pass  # Version may have been deleted; continue without context
        else:
            # Load latest version
            from api.reports.service import get_latest_version
            latest = await get_latest_version(db, thread.report_id)
            if latest:
                report_md = await load_content(latest)

    return messages, report_md


async def delete_thread(
    db: AsyncSession,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Delete a thread and all its messages."""
    thread = await get_thread(db, thread_id, user_id)
    await db.delete(thread)
    await db.commit()
