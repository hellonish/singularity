"""Reports API router — CRUD, versions, export."""
from __future__ import annotations

import difflib
import io
import uuid
from typing import Optional

import markdown as md_lib
from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_redis
from api.db.schemas import (
    PatchRequest,
    PatchResponse,
    ReportListResponse,
    ReportMeta,
    VersionContent,
    VersionListResponse,
    VersionMeta,
)
from api.reports.service import (
    batch_get_latest_versions,
    create_version,
    delete_report,
    get_latest_version,
    get_report,
    get_version_content,
    list_reports,
    list_versions,
    load_content,
)
from api.db.schemas import ThreadResponse
from api.threads.service import get_or_create_default_report_thread
from api.db.models import User

# Maximum length of selected_text accepted in a patch request.
# Prevents CPU exhaustion via expensive SequenceMatcher on large strings.
_MAX_SELECTED_TEXT_LEN = 50_000

router = APIRouter(prefix="/reports", tags=["reports"])


def _report_to_meta(report, latest_version=None) -> ReportMeta:
    return ReportMeta(
        id=report.id,
        title=report.title,
        query=report.query,
        strength=report.strength,
        created_at=report.created_at,
        latest_version=latest_version.version_num if latest_version else None,
        latest_char_count=latest_version.char_count if latest_version else None,
    )


@router.get("", response_model=ReportListResponse)
async def list_user_reports(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    """Cursor-paginated list of the user's reports, newest first."""
    reports, next_cursor = await list_reports(db, current_user.id, cursor, limit)
    # Batch-fetch latest versions in a single query instead of N+1 per report.
    report_ids = [r.id for r in reports]
    latest_by_report = await batch_get_latest_versions(db, report_ids)
    items = [_report_to_meta(r, latest_by_report.get(r.id)) for r in reports]
    return ReportListResponse(items=items, next_cursor=next_cursor)


@router.get("/{report_id}/threads/default", response_model=ThreadResponse)
async def get_or_create_default_report_thread_route(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadResponse:
    """Canonical Q&A thread for this report (creates on first use)."""
    thread = await get_or_create_default_report_thread(db, current_user.id, report_id)
    return ThreadResponse(
        id=thread.id,
        report_id=thread.report_id,
        pinned_version_num=thread.pinned_version_num,
        canonical_report_qa=bool(thread.canonical_report_qa),
        created_at=thread.created_at,
    )


@router.get("/{report_id}", response_model=ReportMeta)
async def get_report_meta(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportMeta:
    """Retrieve metadata for a single report."""
    report = await get_report(db, report_id, current_user.id)
    latest = await get_latest_version(db, report_id)
    return _report_to_meta(report, latest)


@router.delete("/{report_id}", status_code=status.HTTP_200_OK)
async def delete_user_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a report and all its versions."""
    await delete_report(db, report_id, current_user.id)
    return {"status": "deleted"}


@router.get("/{report_id}/versions", response_model=VersionListResponse)
async def list_report_versions(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VersionListResponse:
    """List all versions of a report."""
    versions = await list_versions(db, report_id, current_user.id)
    return VersionListResponse(
        report_id=report_id,
        versions=[
            VersionMeta(
                version_num=v.version_num,
                char_count=v.char_count,
                patch_instruction=v.patch_instruction,
                created_at=v.created_at,
            )
            for v in versions
        ],
    )


@router.get("/{report_id}/versions/{version_num}", response_model=VersionContent)
async def get_version(
    report_id: uuid.UUID,
    version_num: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VersionContent:
    """Get the full content of a specific report version."""
    version = await get_version_content(db, report_id, version_num, current_user.id)
    content = await load_content(version)
    return VersionContent(
        version_num=version.version_num,
        content=content,
        etag=version.content_hash,
        char_count=version.char_count,
    )


@router.post("/{report_id}/versions/{version_num}/patch", response_model=PatchResponse, status_code=status.HTTP_201_CREATED)
async def patch_report_version(
    report_id: uuid.UUID,
    version_num: int,
    body: PatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: ArqRedis = Depends(get_redis),
) -> PatchResponse:
    """
    Submit an edit instruction for a section of the report.

    Uses optimistic locking via If-Match (ETag).  Returns 409 on conflict.
    The actual patch is processed asynchronously; the response returns
    once the patch job is enqueued.
    """
    version = await get_version_content(db, report_id, version_num, current_user.id)

    # Optimistic locking check
    if version.content_hash != body.if_match:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Content has been modified since you last read it. Please refresh.",
        )

    # Guard against CPU exhaustion from SequenceMatcher on very large inputs.
    if len(body.selected_text) > _MAX_SELECTED_TEXT_LEN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"selected_text exceeds maximum length of {_MAX_SELECTED_TEXT_LEN} characters",
        )

    # Verify selected text exists in content
    content = await load_content(version)
    if body.selected_text not in content:
        ratio = difflib.SequenceMatcher(None, body.selected_text, content).quick_ratio()
        if ratio < 0.85:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selected text not found in report content",
            )

    # Enqueue patch job
    job = await redis.enqueue_job(
        "run_patch_job",
        str(report_id),
        version_num,
        str(current_user.id),
        body.selected_text,
        body.instruction,
        body.if_match,
    )

    return PatchResponse(
        new_version_num=version_num + 1,
        etag="pending",
        char_count=0,
    )


@router.get("/{report_id}/versions/{version_num}/export")
async def export_version(
    report_id: uuid.UUID,
    version_num: int,
    format: str = Query("md", regex="^(md|html)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export a report version as markdown or HTML."""
    version = await get_version_content(db, report_id, version_num, current_user.id)
    content = await load_content(version)

    if format == "html":
        html_content = md_lib.markdown(content, extensions=["tables", "fenced_code", "toc"])
        export_content = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Report</title></head><body>{html_content}</body></html>"
        media_type = "text/html"
        filename = f"report_v{version_num}.html"
    else:
        export_content = content
        media_type = "text/markdown"
        filename = f"report_v{version_num}.md"

    buffer = io.BytesIO(export_content.encode("utf-8"))
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
