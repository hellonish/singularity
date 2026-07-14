from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.credential_crypto import decrypt_secret
from api.models import LLMProviderCredential, Report, ResearchRun, ResearchRunEvent, User
from api.schemas import ResearchRunCreate
from api.services.llm_credentials import get_credential, list_credentials
from engine.llm.providers import provider_for
from engine.research_workflow.caps import RunCaps


async def _paid_research_alternatives(
    session: AsyncSession, user_id: str, *, exclude_credential_id: str
) -> list[dict[str, str]]:
    """List the user's other active credentials suitable for a research run.

    Any active non-Groq credential is offered as-is (only Groq has the free
    tier that cannot sustain a run); the blocked Groq credential is excluded.
    We deliberately do not probe each alternative here — that would multiply
    latency and cost at run creation — so the frontend presents them as
    "run with this instead" options rather than pre-verified guarantees.
    """
    alternatives: list[dict[str, str]] = []
    for cred in await list_credentials(session, user_id):
        if cred.id == exclude_credential_id or cred.status != "active":
            continue
        if cred.provider == "groq":
            continue
        alternatives.append(
            {
                "credential_id": cred.id,
                "provider": cred.provider,
                "label": cred.label or provider_for(cred.provider).display_name,
            }
        )
    return alternatives


async def _guard_research_provider_tier(
    session: AsyncSession, user_id: str, credential: LLMProviderCredential, model_id: str | None
) -> None:
    """Block a research run on a free-tier Groq key before any work begins.

    Research spends far more provider calls than a chat turn, and Groq's free
    tier exhausts partway through. We probe the key's daily-request ceiling and
    refuse up front with an actionable error rather than let the run fail
    mid-way. A ``"paid"`` or ``"unknown"`` result proceeds untouched.
    """
    if credential.provider != "groq":
        return
    provider = provider_for("groq")
    probe_model = model_id or credential.default_model_id or settings.groq_fallback_model
    tier = await provider.probe_tier(
        api_key=decrypt_secret(credential.encrypted_secret), model_id=probe_model
    )
    if tier != "free":
        return
    alternatives = await _paid_research_alternatives(
        session, user_id, exclude_credential_id=credential.id
    )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": "research_provider_free_tier",
            "message": (
                "Groq's free plan can't sustain a research run — its per-day "
                "request limit is exhausted partway through. Upgrade to a paid "
                "Groq plan, or run with a paid provider credential."
            ),
            "provider": "groq",
            "alternatives": alternatives,
        },
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RunEventPublisher:
    """Serialize event writes for one active research run.

    Research resolves several DAG nodes concurrently. A single AsyncSession is
    intentionally shared for the run's checkpoint and state writes, so its
    progress events must not concurrently allocate a sequence number or flush.
    """

    def __init__(
        self,
        session: AsyncSession,
        run: ResearchRun,
        *,
        session_lock: asyncio.Lock | None = None,
    ) -> None:
        self._session = session
        self._run = run
        self._lock = session_lock or asyncio.Lock()

    async def append(self, event_type: str, payload: dict) -> ResearchRunEvent:
        async with self._lock:
            return await append_event(self._session, self._run, event_type, payload)


async def get_run(session: AsyncSession, user_id: str, run_id: str) -> ResearchRun:
    result = await session.execute(select(ResearchRun).where(ResearchRun.id == run_id, ResearchRun.user_id == user_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research run not found")
    return run


async def list_runs(session: AsyncSession, user_id: str) -> list[ResearchRun]:
    result = await session.execute(
        select(ResearchRun).where(ResearchRun.user_id == user_id).order_by(ResearchRun.created_at.desc())
    )
    return list(result.scalars())


async def create_run(session: AsyncSession, user: User, body: ResearchRunCreate) -> ResearchRun:
    if not body.provider_credential_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="provider_credential_id is required for a research run",
        )
    if body.test_mode and not settings.research_test_mode:
        # Never silently ignore the flag: reject so a misconfigured server is
        # obvious rather than quietly running a full-cost research run.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="research test mode is not enabled on this server",
        )
    credential = await get_credential(session, user.id, body.provider_credential_id)
    if not (body.test_mode and settings.research_test_mode):
        # Skip the tier probe in test mode: it runs a single minimal node that
        # a free key can complete, and the probe would spend a real call.
        await _guard_research_provider_tier(session, user.id, credential, body.model_id)
    report_id = body.report_id
    if report_id is not None:
        report = await session.get(Report, report_id)
        if report is None or report.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    else:
        report = Report(user_id=user.id, title=body.title, status="processing", source="research")
        session.add(report)
        await session.flush()
        report_id = report.id

    test_mode = bool(body.test_mode and settings.research_test_mode)
    caps = RunCaps.for_test() if test_mode else RunCaps.for_strength(body.strength)
    run = ResearchRun(
        user_id=user.id,
        report_id=report_id,
        query=body.query,
        engine_version=body.engine_version,
        run_data={
            **body.run_data,
            "provider_credential_id": body.provider_credential_id,
            "model_id": body.model_id,
            "strength": body.strength,
            "audience": body.audience,
            "output_language": body.output_language,
            "test_mode": test_mode,
            "caps": caps.__dict__,
        },
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def cancel_run(session: AsyncSession, run: ResearchRun) -> ResearchRun:
    if run.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Research run is already terminal")
    run.status = "cancelled"
    run.finished_at = _now()
    await session.commit()
    await session.refresh(run)
    await append_event(session, run, "research.cancelled", {"status": run.status})
    return run


async def append_event(
    session: AsyncSession,
    run: ResearchRun,
    event_type: str,
    payload: dict,
) -> ResearchRunEvent:
    """Append a monotonic event; the unique key makes replay deterministic."""
    # Locking the aggregate row makes sequence allocation safe for concurrent
    # planner, retrieval, QA, and writer updates in PostgreSQL. SQLite serializes
    # writes here during local development.
    locked_run = await session.scalar(
        select(ResearchRun).where(ResearchRun.id == run.id).with_for_update()
    )
    if locked_run is None:
        raise RuntimeError("cannot append an event for a deleted research run")
    stored_counter = int(locked_run.run_data.get("_event_sequence", 0))
    if stored_counter == 0:
        result = await session.execute(
            select(func.max(ResearchRunEvent.sequence)).where(ResearchRunEvent.run_id == run.id)
        )
        stored_counter = int(result.scalar() or 0)
    sequence = stored_counter + 1
    locked_run.run_data = {**locked_run.run_data, "_event_sequence": sequence}
    event = ResearchRunEvent(
        run_id=run.id,
        sequence=sequence,
        event_type=event_type,
        payload={"run_id": run.id, **payload},
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def list_events(
    session: AsyncSession,
    run: ResearchRun,
    after_sequence: int = 0,
) -> list[ResearchRunEvent]:
    result = await session.execute(
        select(ResearchRunEvent)
        .where(ResearchRunEvent.run_id == run.id, ResearchRunEvent.sequence > after_sequence)
        .order_by(ResearchRunEvent.sequence)
    )
    return list(result.scalars())
