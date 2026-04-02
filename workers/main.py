from __future__ import annotations

import logging

from arq.connections import RedisSettings

from api.config import settings
from workers.patch_job import run_patch_job
from workers.research_job import run_research_job
from workers.summary_job import run_summary_job

logger = logging.getLogger(__name__)


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [run_research_job, run_patch_job, run_summary_job]
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
