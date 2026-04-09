"""
Report service layer.

Handles CRUD for reports and versions, blob storage integration,
and optimistic-locking patch coordination.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.db.models import Report, ReportVersion, User
from storage import get_blob_store

# Content size threshold: inline if smaller, blob otherwise.
_INLINE_THRESHOLD = 500_000  # ~500 KB


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Report listing (cursor-paginated)
# ---------------------------------------------------------------------------

async def list_reports(
    db: AsyncSession,
    user_id: uuid.UUID,
    cursor: Optional[str] = None,
    limit: int = 20,
) -> tuple[list[Report], Optional[str]]:
    """
    Return a page of reports for the user ordered by created_at DESC.

    ``cursor`` is an ISO-format timestamp of the last item's created_at.
    """
    query = (
        select(Report)
        .where(Report.user_id == user_id)
        .order_by(Report.created_at.desc())
        .limit(limit + 1)
    )
    if cursor:
        query = query.where(Report.created_at < datetime.fromisoformat(cursor))

    result = await db.execute(query)
    reports = list(result.scalars().all())

    next_cursor = None
    if len(reports) > limit:
        reports = reports[:limit]
        next_cursor = reports[-1].created_at.isoformat()

    return reports, next_cursor


async def get_report(
    db: AsyncSession,
    report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Report:
    """Fetch a single report with ownership check."""
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.user_id == user_id)
    )
    report: Report | None = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


# ---------------------------------------------------------------------------
# Version management
# ---------------------------------------------------------------------------

async def get_latest_version(
    db: AsyncSession,
    report_id: uuid.UUID,
) -> Optional[ReportVersion]:
    result = await db.execute(
        select(ReportVersion)
        .where(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.version_num.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_versions(
    db: AsyncSession,
    report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[ReportVersion]:
    """List all versions for a report (ownership checked)."""
    await get_report(db, report_id, user_id)
    result = await db.execute(
        select(ReportVersion)
        .where(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.version_num.asc())
    )
    return list(result.scalars().all())


async def get_version_content(
    db: AsyncSession,
    report_id: uuid.UUID,
    version_num: int,
    user_id: uuid.UUID,
) -> ReportVersion:
    """Get a specific version with content loaded from inline or blob storage."""
    await get_report(db, report_id, user_id)

    result = await db.execute(
        select(ReportVersion).where(
            ReportVersion.report_id == report_id,
            ReportVersion.version_num == version_num,
        )
    )
    version: ReportVersion | None = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return version


async def load_content(version: ReportVersion) -> str:
    """
    Load the markdown content for a version from inline storage or blob.
    """
    if version.content_inline is not None:
        return version.content_inline
    if version.content_uri is None:
        return ""
    store = get_blob_store()
    key = version.content_uri.replace("local://", "").replace("s3://", "")
    return await store.read(key)


async def create_version(
    db: AsyncSession,
    report_id: uuid.UUID,
    markdown: str,
    patch_instruction: Optional[str] = None,
) -> ReportVersion:
    """
    Create a new immutable version for a report.

    Content is stored inline if < 500 KB, otherwise written to blob storage.
    """
    content_hash = _content_hash(markdown)
    char_count = len(markdown)

    # Determine next version number
    latest = await get_latest_version(db, report_id)
    version_num = (latest.version_num + 1) if latest else 1

    content_inline: Optional[str] = None
    content_uri: Optional[str] = None

    if char_count < _INLINE_THRESHOLD:
        content_inline = markdown
    else:
        store = get_blob_store()
        key = f"reports/{report_id}/v{version_num}.md"
        uri = await store.write(key, markdown)
        content_uri = uri

    version = ReportVersion(
        report_id=report_id,
        version_num=version_num,
        content_inline=content_inline,
        content_uri=content_uri,
        content_hash=content_hash,
        char_count=char_count,
        patch_instruction=patch_instruction,
        created_at=_now(),
    )
    db.add(version)

    # Auto-set report title from first heading if not set
    report = await get_report(db, report_id, (await db.execute(
        select(Report).where(Report.id == report_id)
    )).scalar_one().user_id)
    if not report.title:
        for line in markdown.splitlines():
            if line.startswith("# "):
                report.title = line[2:].strip()
                break

    await db.commit()
    await db.refresh(version)
    return version


# ---------------------------------------------------------------------------
# Patch (optimistic-locking via ETag)
# ---------------------------------------------------------------------------

async def initiate_patch(
    db: AsyncSession,
    report_id: uuid.UUID,
    version_num: int,
    user_id: uuid.UUID,
    selected_text: str,
    instruction: str,
    if_match: str,
) -> ReportVersion:
    """
    Validate a patch request and enqueue the patch job.

    Uses optimistic locking: the ``if_match`` ETag must match the
    current version's content_hash.  Returns 409 on conflict.
    """
    version = await get_version_content(db, report_id, version_num, user_id)

    # Optimistic locking check
    if version.content_hash != if_match:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Content has been modified since you last read it. Please refresh.",
        )

    # Verify selected_text exists in content (fuzzy match)
    content = await load_content(version)
    if selected_text not in content:
        import difflib
        ratio = difflib.SequenceMatcher(None, selected_text, content).quick_ratio()
        if ratio < 0.85:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selected text not found in report content",
            )

    return version  # Caller enqueues the actual patch job with this context


async def delete_report(
    db: AsyncSession,
    report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Soft-verify ownership and delete a report and all its versions."""
    report = await get_report(db, report_id, user_id)
    await db.delete(report)
    await db.commit()
