from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Report, ResearchRun, ResearchRunEvent, User
from api.schemas import ResearchRunCreate
from api.services.llm_credentials import get_credential
from engine.research_workflow.caps import RunCaps


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
    if not body.provider_credential_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="provider_credential_id is required for a research run",
        )
    await get_credential(session, user.id, body.provider_credential_id)
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
        run_data={
            **body.run_data,
            "provider_credential_id": body.provider_credential_id,
            "model_id": body.model_id,
            "strength": body.strength,
            "audience": body.audience,
            "output_language": body.output_language,
            "caps": RunCaps.for_strength(body.strength).__dict__,
        },
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
    await append_event(session, run, "research.cancelled", {"status": run.status})
    return run


async def append_event(
    session: AsyncSession,
    run: ResearchRun,
    event_type: str,
    payload: dict,
) -> ResearchRunEvent:
    """Append a monotonic event; the unique key makes replay deterministic."""
    # Locking the aggregate row makes sequence allocation safe for concurrent
    # planner, retrieval, QA, and writer updates in PostgreSQL. SQLite serializes
    # writes here during local development.
    locked_run = await session.scalar(
        select(ResearchRun).where(ResearchRun.id == run.id).with_for_update()
    )
    if locked_run is None:
        raise RuntimeError("cannot append an event for a deleted research run")
    stored_counter = int(locked_run.run_data.get("_event_sequence", 0))
    if stored_counter == 0:
        result = await session.execute(
            select(func.max(ResearchRunEvent.sequence)).where(ResearchRunEvent.run_id == run.id)
        )
        stored_counter = int(result.scalar() or 0)
    sequence = stored_counter + 1
    locked_run.run_data = {**locked_run.run_data, "_event_sequence": sequence}
    event = ResearchRunEvent(
        run_id=run.id,
        sequence=sequence,
        event_type=event_type,
        payload={"run_id": run.id, **payload},
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def list_events(
    session: AsyncSession,
    run: ResearchRun,
    after_sequence: int = 0,
) -> list[ResearchRunEvent]:
    result = await session.execute(
        select(ResearchRunEvent)
        .where(ResearchRunEvent.run_id == run.id, ResearchRunEvent.sequence > after_sequence)
        .order_by(ResearchRunEvent.sequence)
    )
    return list(result.scalars())
