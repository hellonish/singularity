from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Report, ReportVersion, ResearchJob
from db.session import AsyncSessionLocal
from storage import get_blob_store

logger = logging.getLogger(__name__)

_INLINE_SIZE_LIMIT = 500_000  # characters


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Redis publishing helpers
# ---------------------------------------------------------------------------


async def _publish_event(
    redis: Any,
    job_id: str,
    event: str,
    data: dict,
    event_id: str | None = None,
) -> None:
    channel = f"job:{job_id}:events"
    payload = {
        "event": event,
        "data": data,
        "id": event_id or str(uuid.uuid4()),
    }
    try:
        await redis.publish(channel, json.dumps(payload))
    except Exception:
        logger.exception("Failed to publish SSE event %s for job %s", event, job_id)


# ---------------------------------------------------------------------------
# CancelToken
# ---------------------------------------------------------------------------


class CancelToken:
    """
    Lightweight cancellation check.

    Raises asyncio.CancelledError when the predicate returns True.
    """

    def __init__(self, predicate) -> None:
        self._predicate = predicate

    def check(self) -> None:
        if self._predicate():
            raise asyncio.CancelledError("Job cancelled via cancel token")


# ---------------------------------------------------------------------------
# create_report_version
# ---------------------------------------------------------------------------


async def create_report_version(
    db: AsyncSession,
    report_id: uuid.UUID,
    markdown: str,
    patch_instruction: str | None = None,
) -> ReportVersion:
    """
    Append a new immutable ReportVersion.

    - If markdown is under 500 KB it is stored inline.
    - Otherwise it is written to the configured BlobStore and content_uri is set.
    - version_num = max(existing) + 1, starting at 1 for the first version.
    """
    # Determine next version number
    result = await db.execute(
        select(func.coalesce(func.max(ReportVersion.version_num), 0)).where(
            ReportVersion.report_id == report_id
        )
    )
    max_ver: int = result.scalar_one() or 0
    next_ver = max_ver + 1

    content_hash = _sha256(markdown)
    char_count = len(markdown)

    if char_count <= _INLINE_SIZE_LIMIT:
        content_inline = markdown
        content_uri = None
    else:
        store = get_blob_store()
        blob_key = f"reports/{report_id}/v{next_ver}.md"
        content_uri = await store.write(blob_key, markdown)
        content_inline = None

    version = ReportVersion(
        report_id=report_id,
        version_num=next_ver,
        content_inline=content_inline,
        content_uri=content_uri,
        content_hash=content_hash,
        char_count=char_count,
        patch_instruction=patch_instruction,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


# ---------------------------------------------------------------------------
# Main worker function
# ---------------------------------------------------------------------------


async def run_research_job(ctx: dict, job_id: str) -> None:
    """
    ARQ worker task — executes one research job end-to-end.

    Lifecycle:
    1. Load job, skip if already terminal (idempotent on re-queue).
    2. Mark running, publish job_status event.
    3. Run the pipeline with phase callbacks that update DB + publish SSE.
    4. On success: save ReportVersion, mark done, publish job_done.
    5. On CancelledError: mark cancelled.
    6. On other Exception: increment attempts; mark failed if exhausted,
       otherwise re-raise so ARQ retries.
    """
    redis = ctx["redis"]

    async with AsyncSessionLocal() as db:
        # Load job
        result = await db.execute(
            select(ResearchJob).where(ResearchJob.id == uuid.UUID(job_id))
        )
        job: ResearchJob | None = result.scalar_one_or_none()
        if job is None:
            logger.warning("run_research_job: job %s not found", job_id)
            return

        # Idempotency guard — skip if already terminal
        if job.status in ("done", "cancelled", "failed"):
            logger.info("run_research_job: job %s already %s, skipping", job_id, job.status)
            return

        # ------------------------------------------------------------------ mark running
        job.status = "running"
        job.started_at = _now()
        await db.commit()
        await db.refresh(job)

        await _publish_event(
            redis,
            job_id,
            "job_status",
            {"status": "running", "phase": None, "description": "Job started"},
        )

        cancel_token = CancelToken(
            lambda: job.expires_at is not None and _now() > job.expires_at
        )

        # ------------------------------------------------------------------ phase callback
        async def phase_callback(phase: str, description: str) -> None:
            cancel_token.check()
            async with AsyncSessionLocal() as phase_db:
                phase_result = await phase_db.execute(
                    select(ResearchJob).where(ResearchJob.id == uuid.UUID(job_id))
                )
                phase_job: ResearchJob | None = phase_result.scalar_one_or_none()
                if phase_job is not None:
                    phase_job.current_phase = phase
                    await phase_db.commit()
            await _publish_event(
                redis,
                job_id,
                "job_status",
                {"status": "running", "phase": phase, "description": description},
            )
            logger.info("Job %s — phase %s: %s", job_id, phase, description)

        # ------------------------------------------------------------------ load query info
        # Always fetch the report explicitly — lazy relationship loading is
        # disabled in async SQLAlchemy and would raise MissingGreenlet.
        report_result = await db.execute(
            select(Report).where(Report.id == job.report_id)
        )
        report_obj = report_result.scalar_one_or_none()
        query: str = report_obj.query if report_obj else ""

        strength = job.strength

        try:
            # Import here to keep the engine clean of HTTP/DB imports at module level
            from agents.orchestrator.pipeline import run_pipeline

            markdown: str = await run_pipeline(
                query=query,
                strength=strength,
            )

            # ---------------------------------------------------------- persist result
            version = await create_report_version(db, job.report_id, markdown)

            # Update report title from first Markdown heading if not already set
            if markdown and report_obj is not None and not report_obj.title:
                first_line = markdown.strip().splitlines()[0] if markdown.strip() else ""
                if first_line.startswith("#"):
                    report_obj.title = first_line.lstrip("#").strip()[:500]

            job.status = "done"
            job.finished_at = _now()
            job.current_phase = None
            await db.commit()

            await _publish_event(
                redis,
                job_id,
                "job_done",
                {
                    "status": "done",
                    "version_num": version.version_num,
                    "report_id": str(job.report_id),
                },
            )
            logger.info("Job %s completed successfully — version %d", job_id, version.version_num)

        except asyncio.CancelledError:
            job.status = "cancelled"
            job.finished_at = _now()
            await db.commit()
            await _publish_event(
                redis,
                job_id,
                "job_cancelled",
                {"status": "cancelled"},
            )
            logger.info("Job %s was cancelled", job_id)

        except Exception as exc:
            job.attempts = (job.attempts or 0) + 1
            exhausted = job.attempts >= job.max_attempts

            if exhausted:
                job.status = "failed"
                job.finished_at = _now()
                job.error_detail = str(exc)[:2000]
                await db.commit()
                await _publish_event(
                    redis,
                    job_id,
                    "job_error",
                    {
                        "status": "failed",
                        "error": str(exc)[:500],
                        "attempts": job.attempts,
                    },
                )
                logger.error(
                    "Job %s failed permanently after %d attempts: %s",
                    job_id,
                    job.attempts,
                    exc,
                    exc_info=True,
                )
            else:
                job.status = "pending"
                await db.commit()
                logger.warning(
                    "Job %s failed (attempt %d/%d) — will retry: %s",
                    job_id,
                    job.attempts,
                    job.max_attempts,
                    exc,
                )
                raise  # Let ARQ handle the retry
