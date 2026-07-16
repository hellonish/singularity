"""ARQ entrypoint for resuming a LangGraph research run.

The graph dependencies are injected by the deployment adapter so this module
does not smuggle provider keys or database credentials into Modal.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from api.config import settings
from api.logging_config import StepLogger, configure_logging
from engine.llm.groq import ProviderError
from engine.research_workflow.runtime import ResearchCancelled, ResearchInfrastructureError

logger = logging.getLogger(__name__)


async def startup(_ctx) -> None:
    """Configure console and file logging before ARQ accepts jobs."""
    configure_logging()


async def _record_failed_run(session, run_id: str, message: str):
    """Persist a terminal failure for both the run and its pending report.

    The report is created before the ARQ job starts. If the job later fails,
    leaving it in ``processing`` hides the failure from the report workspace
    and makes it look as though the worker is still running.
    """
    from api.models import Report, ResearchRun

    await session.rollback()
    run = await session.get(ResearchRun, run_id)
    if run is None:
        return None
    run.status = "failed"
    run.error_message = message
    run.finished_at = datetime.now(timezone.utc)
    if run.report_id:
        report = await session.get(Report, run.report_id)
        # A retry may target an existing ready report. Never invalidate that
        # previous successful version; only transition this run's pending one.
        if report is not None and report.status == "processing":
            report.status = "failed"
    await session.commit()
    return run


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
        step_log = StepLogger("research_worker", user_id=run.user_id, run_id=run.id)
        step_log.step(
            "job",
            phase="start",
            inputs={
                "run_data": {
                    key: value
                    for key, value in run.run_data.items()
                    if key != "sandbox_workspaces"
                },
                "restorable_sandbox_count": len(run.run_data.get("sandbox_workspaces") or []),
                "query": run.query,
            },
        )
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
            step_log.step("job", phase="cancelled")
            await session.rollback()
            run = await session.get(ResearchRun, run_id)
            if run is None:
                return
            run.status = "cancelled"
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()
            await append_event(session, run, "research.cancelled", {"status": run.status})
        except ResearchInfrastructureError as exc:
            step_log.error("job", exc, reason="infrastructure_unavailable")
            # Backend unreachable — surface a friendly "try later" message
            # rather than a raw exception string, and log the detail.
            logger.warning("research run %s aborted: backend unavailable (%s)", run_id, exc)
            run = await _record_failed_run(
                session, run_id, ResearchInfrastructureError.user_message
            )
            if run is None:
                return
            await append_event(session, run, "research.failed", {"status": run.status, "error": run.error_message, "reason": "infrastructure_unavailable"})
        except ProviderError as exc:
            step_log.error("job", exc, code=exc.code)
            # Provider errors are already sanitized by the adapter. Preserve a
            # specific, actionable failure instead of mislabelling a model
            # formatting fault as a progress-recording problem.
            logger.warning("research run %s stopped by provider (%s): %s", run_id, exc.code, exc.message)
            run = await _record_failed_run(session, run_id, exc.message)
            if run is None:
                return
            await append_event(
                session,
                run,
                "research.failed",
                {"status": run.status, "error": run.error_message, "reason": exc.code},
            )
        except Exception as exc:
            step_log.error("job", exc)
            logger.exception("research run %s failed", run_id)
            # A flush failure leaves SQLAlchemy in a pending-rollback state.
            # Reset and reload before persisting a terminal event, otherwise a
            # run remains visibly "researching" forever in the frontend.
            run = await _record_failed_run(
                session,
                run_id,
                "Research could not produce a usable report. Please start a new run.",
            )
            if run is None:
                return
            await append_event(session, run, "research.failed", {"status": run.status, "error": run.error_message})
        else:
            step_log.step("job", phase="end", status="completed")


class WorkerSettings:
    functions = [run_research_job]
    redis_settings = _REDIS_SETTINGS
    max_jobs = 1
    job_timeout = 4 * 60 * 60
    on_startup = startup
