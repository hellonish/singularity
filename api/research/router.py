from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.deps import get_current_user, get_db, get_redis
from api.db.schemas import CreateJobRequest, JobResponse
from api.research.service import cancel_job, create_job, get_job
from api.db.models import ResearchJob, User

router = APIRouter(prefix="/research", tags=["research"])


def _job_to_response(job: ResearchJob) -> JobResponse:
    return JobResponse(
        job_id=str(job.id),
        report_id=str(job.report_id),
        status=job.status,
        current_phase=job.current_phase,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error_detail=job.error_detail,
    )


@router.post("/jobs", response_model=JobResponse)
async def create_research_job(
    body: CreateJobRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: ArqRedis = Depends(get_redis),
) -> JobResponse:
    """
    Submit a new research job.

    Returns 201 on creation, 200 when the idempotency key matches an
    existing job from the last 24 hours.
    """
    job, is_new = await create_job(
        db=db,
        redis=redis,
        user=current_user,
        daily_token_budget=current_user.daily_token_budget,
        request=body,
    )
    response_data = _job_to_response(job)
    http_status = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
    return JSONResponse(
        content=response_data.model_dump(mode="json"),
        status_code=http_status,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_research_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Retrieve the current status of a research job."""
    job = await get_job(db, job_id, current_user.id)
    return _job_to_response(job)


@router.get("/jobs/{job_id}/events")
async def stream_job_events(
    job_id: uuid.UUID,
    request: Request,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
    redis: ArqRedis = Depends(get_redis),
) -> StreamingResponse:
    """
    SSE stream for real-time job progress updates.

    Authentication: pass the short-lived SSE token (from GET /auth/sse-token)
    as the `token` query parameter, since EventSource cannot set headers.

    Supports `Last-Event-ID` header for resuming after reconnect.

    Events include coarse ``job_status`` (phase rail) and append-only ``job_activity``
    (storyboard). Redis pub/sub is not durable: clients that connect after a job
    finishes receive a terminal snapshot from the DB but not historical ``job_activity``.
    """
    # Authenticate via short-lived SSE token or fall back to regular bearer
    auth_header = request.headers.get("Authorization")
    raw_token = token
    if not raw_token and auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header.split(" ", 1)[1]

    if not raw_token:
        raise HTTPException(status_code=401, detail="SSE authentication required")

    try:
        payload = jwt.decode(raw_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise JWTError("no sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid SSE token")

    user_id = uuid.UUID(user_id_str)

    # Verify job ownership
    job = await get_job(db, job_id, user_id)

    # Last-Event-ID is captured for future cursor-based resumption.
    # Currently the SSE stream re-subscribes from the live position;
    # historical event replay requires a persistent event log (future work).
    _last_event_id = request.headers.get("Last-Event-ID")  # noqa: F841

    async def event_generator() -> AsyncGenerator[bytes, None]:
        channel = f"job:{job_id}:events"
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        # If the job is already terminal, emit its final state immediately
        current_job = job
        if current_job.status in ("done", "failed", "cancelled"):
            event_type = {
                "done": "job_done",
                "failed": "job_error",
                "cancelled": "job_cancelled",
            }.get(current_job.status, "job_status")
            term_payload: dict = {
                "status": current_job.status,
                "current_phase": current_job.current_phase,
                "error_detail": current_job.error_detail,
            }
            if current_job.started_at and current_job.finished_at:
                term_payload["elapsed_ms"] = int(
                    (current_job.finished_at - current_job.started_at).total_seconds()
                    * 1000
                )
            data = json.dumps(term_payload)
            yield f"event: {event_type}\ndata: {data}\n\n".encode()
            await pubsub.unsubscribe(channel)
            return

        try:
            async for message in pubsub.listen():
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                if message["type"] != "message":
                    continue

                raw = message["data"]
                if isinstance(raw, bytes):
                    raw = raw.decode()

                try:
                    payload_data = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    continue

                event_type = payload_data.get("event", "job_status")
                event_data = json.dumps(payload_data.get("data", {}))
                event_id = payload_data.get("id", "")

                sse_line = f"id: {event_id}\nevent: {event_type}\ndata: {event_data}\n\n"
                yield sse_line.encode()

                # Stop streaming once a terminal event is received
                if event_type in ("job_done", "job_error", "job_cancelled"):
                    break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/jobs/{job_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_research_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Request cancellation of a running or pending job."""
    job = await cancel_job(db, job_id, current_user.id)
    return {"job_id": str(job.id), "status": job.status}
