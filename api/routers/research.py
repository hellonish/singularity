from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from api.dependencies import CurrentUserDep, SessionDep
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
    """Queue a durable run. Worker dispatch belongs to the future engine integration."""

    return await research_service.create_run(session, current_user, body)


@router.get("/runs/{run_id}", response_model=ResearchRunRead)
async def get_run(run_id: str, session: SessionDep, current_user: CurrentUserDep) -> ResearchRunRead:
    return await research_service.get_run(session, current_user.id, run_id)


@router.post("/runs/{run_id}/cancel", response_model=ResearchRunRead)
async def cancel_run(run_id: str, session: SessionDep, current_user: CurrentUserDep) -> ResearchRunRead:
    run = await research_service.get_run(session, current_user.id, run_id)
    return await research_service.cancel_run(session, run)


@router.get("/runs/{run_id}/events")
async def stream_run_events(run_id: str, session: SessionDep, current_user: CurrentUserDep) -> StreamingResponse:
    """SSE response shape for the engine's future progress-event publisher."""

    run = await research_service.get_run(session, current_user.id, run_id)

    async def events() -> AsyncIterator[str]:
        payload = {"run_id": run.id, "status": run.status, "report_id": run.report_id}
        yield encode_sse(event="research.status", event_id=f"{run.id}:status", data=payload)
        if run.status in {"completed", "failed", "cancelled"}:
            yield encode_sse(
                event="research.completed",
                event_id=f"{run.id}:completed",
                data={"run_id": run.id, "status": run.status},
            )

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)
