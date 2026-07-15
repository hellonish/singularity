from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from api.config import settings
from api.dependencies import CurrentUserDep, SessionDep
from api.research_preparation_runtime import ResearchPreparationError
from api.research_preparation_runtime import create_preparation as prepare_research
from api.research_preparation_runtime import finalize_after_answers
from api.research_queue import enqueue_research_run
from api.schemas import (
    ResearchPreparationAnswerCreate,
    ResearchPreparationCreate,
    ResearchPreparationRead,
    ResearchPreparationResult,
    ResearchRunCreate,
    ResearchRunRead,
)
from api.services import research as research_service
from api.sse import SSE_HEADERS, encode_sse

router = APIRouter(prefix="/research", tags=["research"])


def _require_worker() -> None:
    if not settings.research_worker_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="research worker is not enabled; start the worker before creating research",
        )


async def _dispatch_run(session: SessionDep, run) -> None:
    await research_service.append_event(session, run, "research.queued", {"status": run.status})
    dispatched = await enqueue_research_run(run.id)
    if not dispatched:
        run.status = "failed"
        run.error_message = "research job could not be dispatched to the worker"
        await session.commit()
        await research_service.append_event(
            session,
            run,
            "research.failed",
            {"status": run.status, "error": run.error_message},
        )


@router.post(
    "/preparations",
    response_model=ResearchPreparationResult,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_research_preparation(
    body: ResearchPreparationCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ResearchPreparationResult:
    """Prepare a bounded plan, then pause in Ask mode or dispatch in Auto mode."""

    _require_worker()
    try:
        preparation, run = await prepare_research(session, current_user, body)
    except ResearchPreparationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if run is not None:
        await _dispatch_run(session, run)
    return ResearchPreparationResult(preparation=preparation, run=run)


@router.get("/preparations/{preparation_id}", response_model=ResearchPreparationRead)
async def get_research_preparation(
    preparation_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ResearchPreparationRead:
    return await research_service.get_preparation(session, current_user.id, preparation_id)


@router.post(
    "/preparations/{preparation_id}/answers",
    response_model=ResearchPreparationRead,
)
async def answer_research_preparation(
    preparation_id: str,
    body: ResearchPreparationAnswerCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ResearchPreparationRead:
    preparation = await research_service.get_preparation(session, current_user.id, preparation_id)
    preparation, complete = await research_service.record_preparation_answer(
        session,
        preparation,
        question_id=body.question_id,
        answer=body.answer,
    )
    if complete:
        try:
            preparation = await finalize_after_answers(session, current_user, preparation)
        except ResearchPreparationError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return preparation


@router.post(
    "/preparations/{preparation_id}/start",
    response_model=ResearchRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_research_preparation(
    preparation_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ResearchRunRead:
    _require_worker()
    preparation = await research_service.get_preparation(session, current_user.id, preparation_id)
    already_started = preparation.status == "started"
    run = await research_service.start_preparation(session, current_user, preparation)
    if run.status == "queued" and not already_started:
        await _dispatch_run(session, run)
    return run


@router.delete("/preparations/{preparation_id}", response_model=ResearchPreparationRead)
async def cancel_research_preparation(
    preparation_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ResearchPreparationRead:
    preparation = await research_service.get_preparation(session, current_user.id, preparation_id)
    return await research_service.cancel_preparation(session, preparation)


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

    _require_worker()

    run = await research_service.create_run(session, current_user, body)
    await _dispatch_run(session, run)
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
