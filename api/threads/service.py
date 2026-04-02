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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.reports.service import get_report, get_version_content, load_content
from db.models import Message, Report, Thread, User


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
    """List user's threads, newest first."""
    result = await db.execute(
        select(Thread)
        .where(Thread.user_id == user_id)
        .order_by(Thread.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


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
