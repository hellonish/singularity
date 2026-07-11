from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Report, ResearchRun, User
from api.schemas import ResearchRunCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_run(session: AsyncSession, user_id: str, run_id: str) -> ResearchRun:
    result = await session.execute(select(ResearchRun).where(ResearchRun.id == run_id, ResearchRun.user_id == user_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research run not found")
    return run


async def list_runs(session: AsyncSession, user_id: str) -> list[ResearchRun]:
    result = await session.execute(
        select(ResearchRun).where(ResearchRun.user_id == user_id).order_by(ResearchRun.created_at.desc())
    )
    return list(result.scalars())


async def create_run(session: AsyncSession, user: User, body: ResearchRunCreate) -> ResearchRun:
    report_id = body.report_id
    if report_id is not None:
        report = await session.get(Report, report_id)
        if report is None or report.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    else:
        report = Report(user_id=user.id, title=body.title, status="processing", source="research")
        session.add(report)
        await session.flush()
        report_id = report.id

    run = ResearchRun(
        user_id=user.id,
        report_id=report_id,
        query=body.query,
        engine_version=body.engine_version,
        run_data=body.run_data,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def cancel_run(session: AsyncSession, run: ResearchRun) -> ResearchRun:
    if run.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Research run is already terminal")
    run.status = "cancelled"
    run.finished_at = _now()
    await session.commit()
    await session.refresh(run)
    return run
