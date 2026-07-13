from __future__ import annotations

import logging

from api.config import settings

logger = logging.getLogger(__name__)


async def enqueue_research_run(run_id: str) -> bool:
    """Best-effort ARQ dispatch; durable status remains queued on broker outage."""
    if not settings.research_worker_enabled:
        return False
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
    except ImportError:
        logger.error("research worker enabled but arq is not installed")
        return False
    try:
        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    except Exception:
        logger.exception("research run dispatch could not connect to Redis")
        return False
    try:
        await pool.enqueue_job("run_research_job", run_id)
        return True
    except Exception:
        logger.exception("research run dispatch failed")
        return False
    finally:
        await pool.close()
