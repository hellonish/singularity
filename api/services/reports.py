from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Report, ReportVersion, User
from api.schemas import ReportCreate, ReportVersionCreate
from api.storage import ObjectStore


async def get_report(session: AsyncSession, user_id: str, report_id: str) -> Report:
    result = await session.execute(select(Report).where(Report.id == report_id, Report.user_id == user_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


async def list_reports(session: AsyncSession, user_id: str) -> list[Report]:
    result = await session.execute(
        select(Report)
        .where(Report.user_id == user_id, Report.status != "archived")
        .order_by(Report.created_at.desc())
    )
    return list(result.scalars())


async def archive_report(session: AsyncSession, report: Report) -> Report:
    report.status = "archived"
    await session.commit()
    await session.refresh(report)
    return report


async def create_report(session: AsyncSession, user: User, body: ReportCreate) -> Report:
    report = Report(user_id=user.id, title=body.title, source=body.source, report_data=body.report_data)
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def list_versions(session: AsyncSession, report: Report) -> list[ReportVersion]:
    result = await session.execute(
        select(ReportVersion).where(ReportVersion.report_id == report.id).order_by(ReportVersion.version_number.desc())
    )
    return list(result.scalars())


async def get_latest_version(session: AsyncSession, report: Report) -> ReportVersion | None:
    result = await session.execute(
        select(ReportVersion)
        .where(ReportVersion.report_id == report.id)
        .order_by(ReportVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_version(session: AsyncSession, report: Report, version_id: str) -> ReportVersion:
    result = await session.execute(
        select(ReportVersion).where(
            ReportVersion.id == version_id,
            ReportVersion.report_id == report.id,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report version not found")
    return version


async def create_version(
    session: AsyncSession,
    report: Report,
    body: ReportVersionCreate,
    store: ObjectStore,
) -> ReportVersion:
    last_number = await session.scalar(
        select(func.coalesce(func.max(ReportVersion.version_number), 0)).where(ReportVersion.report_id == report.id)
    )
    version_number = int(last_number or 0) + 1
    content_bytes = body.content.encode("utf-8")
    metadata = await store.put_bytes(
        f"reports/{report.id}/versions/{version_number}.md",
        content_bytes,
        content_type="text/markdown; charset=utf-8",
    )
    version = ReportVersion(
        report_id=report.id,
        version_number=version_number,
        parent_version_id=body.parent_version_id,
        content=None,
        content_uri=metadata.uri,
        content_size_bytes=metadata.size_bytes,
        content_format=body.content_format,
        checksum=metadata.checksum_sha256,
        change_note=body.change_note,
        version_data=body.version_data,
    )
    session.add(version)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        await store.delete(metadata.uri)
        raise
    await session.refresh(version)
    return version


async def read_version_content(version: ReportVersion, store: ObjectStore) -> str:
    if version.content is not None:
        return version.content
    if version.content_uri is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Version has no content")
    try:
        return (await store.get_bytes(version.content_uri)).decode("utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored version content not found") from exc
