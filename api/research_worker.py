"""ARQ entrypoint for resuming a LangGraph research run.

The graph dependencies are injected by the deployment adapter so this module
does not smuggle provider keys or database credentials into Modal.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from api.config import settings
from engine.research_workflow.runtime import ResearchCancelled, ResearchInfrastructureError

logger = logging.getLogger(__name__)

try:  # Keep API/unit-test imports usable before optional worker dependencies install.
    from arq.connections import RedisSettings
    _REDIS_SETTINGS = RedisSettings.from_dsn(settings.redis_url)
except ImportError:  # pragma: no cover - exercised only in minimal API images
    _REDIS_SETTINGS = None


async def run_research_job(ctx, run_id: str) -> None:
    """Resume one graph thread. Adapter setup is deliberately explicit."""
    from api.database import SessionLocal
    from api.models import ResearchRun
    from sqlalchemy import select

    async with SessionLocal() as session:
        result = await session.execute(select(ResearchRun).where(ResearchRun.id == run_id))
        run = result.scalar_one_or_none()
        if run is None or run.status in {"cancelled", "completed", "failed"}:
            return
        run.status = "running"
        run.started_at = run.started_at or datetime.now(timezone.utc)
        await session.commit()
        from api.services.research import append_event
        await append_event(session, run, "research.running", {"status": run.status})
        try:
            from api.research_runtime import execute_research_run
            await execute_research_run(run=run, session=session)
            await append_event(session, run, "research.completed", {"status": run.status})
        except ResearchCancelled:
            run.status = "cancelled"
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()
            await append_event(session, run, "research.cancelled", {"status": run.status})
        except ResearchInfrastructureError as exc:
            # Backend unreachable — surface a friendly "try later" message
            # rather than a raw exception string, and log the detail.
            logger.warning("research run %s aborted: backend unavailable (%s)", run_id, exc)
            run.status = "failed"
            run.error_message = ResearchInfrastructureError.user_message
            await session.commit()
            await append_event(session, run, "research.failed", {"status": run.status, "error": run.error_message, "reason": "infrastructure_unavailable"})
        except Exception as exc:
            logger.exception("research run %s failed", run_id)
            run.status = "failed"
            run.error_message = str(exc)[:2_000]
            await session.commit()
            await append_event(session, run, "research.failed", {"status": run.status, "error": run.error_message})


class WorkerSettings:
    functions = [run_research_job]
    redis_settings = _REDIS_SETTINGS
    max_jobs = 1
    job_timeout = 4 * 60 * 60
