"""Research worker failures must leave both the run and report terminal."""
from __future__ import annotations

import asyncio

import api.research_runtime as research_runtime
from api.database import SessionLocal
from api.models import Report, ResearchRun, User
from api.research_worker import run_research_job


def test_worker_marks_the_pending_report_failed_when_generation_fails(monkeypatch) -> None:
    async def create_run() -> tuple[str, str]:
        async with SessionLocal() as session:
            user = User(display_name="Research user")
            session.add(user)
            await session.flush()
            report = Report(user_id=user.id, title="Pending report", status="processing", source="research")
            session.add(report)
            await session.flush()
            run = ResearchRun(user_id=user.id, report_id=report.id, query="Investigate the repository")
            session.add(run)
            await session.commit()
            return run.id, report.id

    async def fail_generation(*, run, session) -> None:
        raise ValueError("writer returned no usable sections")

    run_id, report_id = asyncio.run(create_run())
    monkeypatch.setattr(research_runtime, "execute_research_run", fail_generation)

    asyncio.run(run_research_job({}, run_id))

    async def read_result() -> tuple[ResearchRun, Report]:
        async with SessionLocal() as session:
            run = await session.get(ResearchRun, run_id)
            report = await session.get(Report, report_id)
            assert run is not None
            assert report is not None
            return run, report

    run, report = asyncio.run(read_result())
    assert run.status == "failed"
    assert run.error_message == "Research could not produce a usable report. Please start a new run."
    assert report.status == "failed"
