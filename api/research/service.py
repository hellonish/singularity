from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from arq import ArqRedis
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.research.schemas import CreateJobRequest
from db.models import Report, ResearchJob, UsageEvent, User


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _check_daily_quota(db: AsyncSession, user_id: uuid.UUID, daily_token_budget: int) -> None:
    """
    Sum prompt_tokens + completion_tokens from today's usage events.
    Raises 429 if the user is over budget.
    """
    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.prompt_tokens), 0)
            + func.coalesce(func.sum(UsageEvent.completion_tokens), 0)
        ).where(
            UsageEvent.user_id == user_id,
            UsageEvent.created_at >= today_start,
        )
    )
    tokens_used: int = result.scalar_one() or 0
    if tokens_used >= daily_token_budget:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily token budget exhausted. Try again tomorrow.",
        )


async def _check_concurrent_limit(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Raise 429 if user already has max_concurrent_jobs_per_user running jobs."""
    result = await db.execute(
        select(func.count(ResearchJob.id)).where(
            ResearchJob.user_id == user_id,
            ResearchJob.status.in_(["pending", "running"]),
        )
    )
    active: int = result.scalar_one() or 0
    if active >= settings.max_concurrent_jobs_per_user:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum of {settings.max_concurrent_jobs_per_user} concurrent jobs allowed.",
        )


async def _find_idempotent_job(
    db: AsyncSession,
    user_id: uuid.UUID,
    idempotency_key: str,
) -> ResearchJob | None:
    """Return an existing job with this key created within the last 24 hours."""
    cutoff = _now() - timedelta(hours=24)
    result = await db.execute(
        select(ResearchJob).where(
            ResearchJob.user_id == user_id,
            ResearchJob.idempotency_key == idempotency_key,
            ResearchJob.created_at >= cutoff,
        )
    )
    return result.scalar_one_or_none()


async def create_job(
    db: AsyncSession,
    redis: ArqRedis,
    user: User,
    daily_token_budget: int,
    request: CreateJobRequest,
) -> tuple[ResearchJob, bool]:
    """
    Create a new research job (or return existing on idempotency hit).

    Returns (job, is_new) where is_new=False means the idempotency key matched
    an existing job within the last 24 h.
    """
    user_id = user.id

    # Idempotency check first — skip quota/concurrency check for duplicates
    if request.idempotency_key:
        existing = await _find_idempotent_job(db, user_id, request.idempotency_key)
        if existing is not None:
            return existing, False

    await _check_daily_quota(db, user_id, daily_token_budget)
    await _check_concurrent_limit(db, user_id)

    from api.llm_credentials_service import (
        get_decrypted_provider_key,
        model_provider,
        validate_model_id,
    )

    job_model_id = validate_model_id(request.model_id)

    prov = model_provider(job_model_id)
    pk = await get_decrypted_provider_key(db, user_id, prov)
    if not pk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Add your {prov} API key in Profile → LLM keys to run research with this model.",
        )

    # Create report row
    report = Report(
        user_id=user_id,
        query=request.query,
        strength=request.strength,
    )
    db.add(report)
    await db.flush()  # populate report.id

    # Create job row
    job = ResearchJob(
        report_id=report.id,
        user_id=user_id,
        idempotency_key=request.idempotency_key,
        status="pending",
        strength=request.strength,
        llm_model_id=job_model_id,
        attempts=0,
        max_attempts=3,
        created_at=_now(),
        expires_at=_now() + timedelta(minutes=35),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await redis.enqueue_job("run_research_job", str(job.id))

    return job, True


async def get_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ResearchJob:
    """Fetch a job with ownership check. Raises 404 if not found or wrong owner."""
    result = await db.execute(
        select(ResearchJob).where(
            ResearchJob.id == job_id,
            ResearchJob.user_id == user_id,
        )
    )
    job: ResearchJob | None = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research job not found",
        )
    return job


async def cancel_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ResearchJob:
    """
    Request cancellation of a pending or running job.

    Sets status to 'cancelled' if the job has not yet finished.
    The worker checks expires_at / status so setting expires_at to now
    acts as a cancellation signal when the job is already running.
    """
    job = await get_job(db, job_id, user_id)
    if job.status in ("done", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is already in terminal state: {job.status}",
        )
    # Signal cancellation: set expires_at to now so the cancel token fires
    job.status = "cancelled"
    job.finished_at = _now()
    await db.commit()
    await db.refresh(job)
    return job
