from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
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


def _as_utc_aware(dt: datetime | None) -> datetime | None:
    """
    Normalize ORM-loaded datetimes for comparison with _now().

    asyncpg/SQLAlchemy may return naive timestamps for TIMESTAMPTZ columns; comparing
    those to timezone-aware UTC raises TypeError in Python 3.12+.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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

        job_start = job.started_at

        await _publish_event(
            redis,
            job_id,
            "job_status",
            {"status": "running", "phase": None, "description": "Job started", "elapsed_ms": 0},
        )

        cancel_token = CancelToken(
            lambda: job.expires_at is not None
            and _now() > _as_utc_aware(job.expires_at)
        )

        def _elapsed_ms() -> int:
            if job_start is None:
                return 0
            start = _as_utc_aware(job_start)
            if start is None:
                return 0
            return int((_now() - start).total_seconds() * 1000)

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
                {
                    "status": "running",
                    "phase": phase,
                    "description": description,
                    "elapsed_ms": _elapsed_ms(),
                },
            )
            logger.info("Job %s — phase %s: %s", job_id, phase, description)

        async def activity_callback(payload: dict) -> None:
            cancel_token.check()
            merged = {**payload, "elapsed_ms": _elapsed_ms()}
            await _publish_event(redis, job_id, "job_activity", merged)

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
            from agents.chat.models import DEFAULT_MODEL_ID, MODEL_MAP
            from agents.orchestrator.pipeline import run_pipeline
            from api.llm_credentials_service import (
                get_decrypted_provider_key,
                model_provider,
            )

            mid = (job.llm_model_id or "").strip() or DEFAULT_MODEL_ID
            if mid not in MODEL_MAP:
                mid = DEFAULT_MODEL_ID
            prov = model_provider(mid)
            llm_key = await get_decrypted_provider_key(db, job.user_id, prov)
            if not llm_key:
                raise RuntimeError(
                    f"Missing {prov} API key for this user; add it under Profile → LLM keys."
                )

            markdown: str = await run_pipeline(
                query=query,
                strength=strength,
                on_phase=phase_callback,
                on_activity=activity_callback,
                model_id=mid,
                llm_api_key=llm_key,
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
                    "elapsed_ms": _elapsed_ms(),
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
                {"status": "cancelled", "elapsed_ms": _elapsed_ms()},
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
                        "elapsed_ms": _elapsed_ms(),
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


_DEBUG_MOCK_REPORT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "debug_mock_report.md"

_MOCK_PHASES: list[tuple[str, str]] = [
    ("planning", "Structuring sections from your query…"),
    ("retrieval", "Gathering sources (mock, no network)…"),
    ("writing", "Drafting report body…"),
    ("polish", "Polishing markdown…"),
]


async def run_debug_mock_research_job(ctx: dict, job_id: str) -> None:
    """
    Integration-test job: publishes the same SSE shapes as run_research_job
    but writes a static fixture as the report version (no LLM / pipeline).
    """
    redis = ctx["redis"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ResearchJob).where(ResearchJob.id == uuid.UUID(job_id))
        )
        job: ResearchJob | None = result.scalar_one_or_none()
        if job is None:
            logger.warning("run_debug_mock_research_job: job %s not found", job_id)
            return

        if job.status in ("done", "cancelled", "failed"):
            logger.info(
                "run_debug_mock_research_job: job %s already %s, skipping",
                job_id,
                job.status,
            )
            return

        job.status = "running"
        job.started_at = _now()
        await db.commit()
        await db.refresh(job)

        job_start = job.started_at

        def _mock_elapsed_ms() -> int:
            if job_start is None:
                return 0
            start = _as_utc_aware(job_start)
            if start is None:
                return 0
            return int((_now() - start).total_seconds() * 1000)

        async def _mock_activity(kind: str, phase: str, meta: dict | None = None) -> None:
            await _publish_event(
                redis,
                job_id,
                "job_activity",
                {
                    "kind": kind,
                    "phase": phase,
                    "meta": {**(meta or {}), "mock": True},
                    "elapsed_ms": _mock_elapsed_ms(),
                },
            )

        await _publish_event(
            redis,
            job_id,
            "job_status",
            {
                "status": "running",
                "phase": None,
                "description": "Mock job started (debug)",
                "elapsed_ms": 0,
            },
        )

        await _mock_activity(
            "pipeline_start",
            "planning",
            {"strength": job.strength, "run_id": "debug-mock"},
        )
        await _mock_activity(
            "domain_classified",
            "planning",
            {"label": "debug-mock", "confidence": "n/a"},
        )
        await _mock_activity(
            "managers_spawn",
            "planning",
            {"perspectives": ["mock"], "note": "Planning managers skipped in mock job"},
        )

        report_result = await db.execute(select(Report).where(Report.id == job.report_id))
        report_obj: Report | None = report_result.scalar_one_or_none()

        try:
            for phase, description in _MOCK_PHASES:
                await asyncio.sleep(0.35)
                async with AsyncSessionLocal() as phase_db:
                    pr = await phase_db.execute(
                        select(ResearchJob).where(ResearchJob.id == uuid.UUID(job_id))
                    )
                    pj = pr.scalar_one_or_none()
                    if pj is not None:
                        pj.current_phase = phase
                        await phase_db.commit()
                if phase == "retrieval":
                    await _mock_activity(
                        "retrieval_plan_ready",
                        "retrieval",
                        {"skills": ["web_search"], "queries_per_skill": {"web_search": 1}},
                    )
                    await _mock_activity(
                        "retrieval_skill_finished",
                        "retrieval",
                        {"skill": "web_search", "sources_found": 0, "chunks_stored": 0},
                    )
                if phase == "writing":
                    await _mock_activity(
                        "writers_depth",
                        "writing",
                        {"depth": 1, "node_count": 1},
                    )
                if phase == "polish":
                    await _mock_activity("polish_started", "polish", {"section_count": 1})
                await _publish_event(
                    redis,
                    job_id,
                    "job_status",
                    {
                        "status": "running",
                        "phase": phase,
                        "description": description,
                        "elapsed_ms": _mock_elapsed_ms(),
                    },
                )

            markdown = _DEBUG_MOCK_REPORT_FIXTURE.read_text(encoding="utf-8")
            version = await create_report_version(db, job.report_id, markdown)

            if report_obj is not None and not report_obj.title:
                first = markdown.strip().splitlines()[0] if markdown.strip() else ""
                if first.startswith("#"):
                    report_obj.title = first.lstrip("#").strip()[:500]

            await _mock_activity(
                "polish_finished",
                "polish",
                {"char_count": len(markdown)},
            )

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
                    "elapsed_ms": _mock_elapsed_ms(),
                },
            )
            logger.info(
                "run_debug_mock_research_job %s completed — version %s",
                job_id,
                version.version_num,
            )

        except Exception as exc:
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
                    "attempts": job.attempts or 1,
                    "elapsed_ms": _mock_elapsed_ms(),
                },
            )
            logger.exception("run_debug_mock_research_job %s failed", job_id)
