from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from api.config import settings
from api.dependencies import CurrentUserDep, SessionDep
from api.research_queue import enqueue_research_run
from api.schemas import ResearchRunCreate, ResearchRunRead
from api.services import research as research_service
from api.sse import SSE_HEADERS, encode_sse

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/runs", response_model=list[ResearchRunRead])
async def list_runs(session: SessionDep, current_user: CurrentUserDep) -> list[ResearchRunRead]:
    return await research_service.list_runs(session, current_user.id)


@router.post("/runs", response_model=ResearchRunRead, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    body: ResearchRunCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ResearchRunRead:
    """Queue a durable run for the configured ARQ worker."""

    if not settings.research_worker_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="research worker is not enabled; use the CLI demo or start the worker before creating a run",
        )

    run = await research_service.create_run(session, current_user, body)
    await research_service.append_event(session, run, "research.queued", {"status": run.status})
    dispatched = await enqueue_research_run(run.id)
    if not dispatched and settings.research_worker_enabled:
        run.status = "failed"
        run.error_message = "research job could not be dispatched to the worker"
        await session.commit()
        await research_service.append_event(session, run, "research.failed", {"status": run.status, "error": run.error_message})
    return run


@router.get("/runs/{run_id}", response_model=ResearchRunRead)
async def get_run(run_id: str, session: SessionDep, current_user: CurrentUserDep) -> ResearchRunRead:
    return await research_service.get_run(session, current_user.id, run_id)


@router.post("/runs/{run_id}/cancel", response_model=ResearchRunRead)
async def cancel_run(run_id: str, session: SessionDep, current_user: CurrentUserDep) -> ResearchRunRead:
    run = await research_service.get_run(session, current_user.id, run_id)
    return await research_service.cancel_run(session, run)


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """Replay durable events and keep the connection open until a terminal one."""

    run = await research_service.get_run(session, current_user.id, run_id)

    async def events() -> AsyncIterator[str]:
        try:
            after = int(last_event_id or 0)
        except ValueError:
            after = 0
        from api.database import SessionLocal
        while True:
            async with SessionLocal() as stream_session:
                current = await research_service.get_run(stream_session, current_user.id, run.id)
                rows = await research_service.list_events(stream_session, current, after)
                for event_row in rows:
                    after = event_row.sequence
                    yield encode_sse(
                        event=event_row.event_type,
                        event_id=str(event_row.sequence),
                        data=event_row.payload,
                    )
                if not rows:
                    yield encode_sse(event="research.heartbeat", data={"run_id": current.id, "status": current.status})
                # Terminal transitions are persisted by the worker/service and
                # replayed above.  Do not manufacture a second terminal event
                # with a duplicated Last-Event-ID (or the wrong event type).
                if current.status in {"completed", "failed", "cancelled"}:
                    break
            await asyncio.sleep(1.0)

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)
