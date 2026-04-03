from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from arq.connections import RedisSettings
from sqlalchemy import select

from api.config import settings
from db.models import ResearchJob
from db.session import AsyncSessionLocal
from workers.patch_job import run_patch_job
from workers.research_job import run_debug_mock_research_job, run_research_job
from workers.summary_job import run_summary_job

logger = logging.getLogger(__name__)


async def _recover_orphaned_jobs(redis) -> None:
    """
    On worker startup, any job still in 'running' state was interrupted by a
    previous crash. Mark them failed and publish job_error so the frontend
    SSE stream or polling fallback surfaces the error immediately.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ResearchJob).where(ResearchJob.status == "running")
        )
        orphans = result.scalars().all()

        if not orphans:
            return

        for job in orphans:
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            job.error_detail = "Worker process restarted unexpectedly. Please retry."
        await db.commit()

        for job in orphans:
            payload = json.dumps({
                "event": "job_error",
                "data": {
                    "status": "failed",
                    "error": "Worker process restarted unexpectedly. Please retry.",
                    "attempts": job.attempts or 1,
                    "elapsed_ms": 0,
                },
                "id": str(uuid.uuid4()),
            })
            await redis.publish(f"job:{job.id}:events", payload)
            logger.warning("Recovered orphaned job %s → failed", job.id)


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [run_research_job, run_debug_mock_research_job, run_patch_job, run_summary_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    # Concurrency / timeout
    max_jobs = 4
    job_timeout = 1800  # 30 minutes per job

    # Result retention
    keep_result = 3600  # keep job result for 1 hour

    # Retry behaviour
    retry_jobs = True
    max_tries = 3

    @staticmethod
    async def on_startup(ctx: dict) -> None:
        """Called once when the worker process starts."""
        import redis.asyncio as aioredis

        redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        ctx["redis"] = redis
        logger.info("ARQ worker started — redis: %s", settings.redis_url)
        await _recover_orphaned_jobs(redis)

    @staticmethod
    async def on_shutdown(ctx: dict) -> None:
        """Called once when the worker process shuts down."""
        redis = ctx.get("redis")
        if redis is not None:
            await redis.aclose()
        logger.info("ARQ worker shut down")


if __name__ == "__main__":
    import asyncio

    from arq import run_worker

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_worker(WorkerSettings)
