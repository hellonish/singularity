from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from api.database import SessionLocal
from api.models import ResearchRun, ResearchRunEvent
from api.services.research import RunEventPublisher, cancel_run
from engine.research_workflow.runtime import ResearchCancelled


def test_parallel_progress_events_receive_unique_sequences(
    client,
    current_user: dict[str, str],
) -> None:
    async def run_test() -> None:
        async with SessionLocal() as session:
            run = ResearchRun(user_id=current_user["X-User-ID"], query="Concurrent event test")
            session.add(run)
            await session.commit()
            await session.refresh(run)

            publisher = RunEventPublisher(session, run)
            await asyncio.gather(*(
                publisher.append("research.progress", {"status": "node_started", "node": index})
                for index in range(6)
            ))

            events = list((await session.scalars(
                select(ResearchRunEvent)
                .where(ResearchRunEvent.run_id == run.id)
                .order_by(ResearchRunEvent.sequence)
            )).all())
            assert [event.sequence for event in events] == [1, 2, 3, 4, 5, 6]

    asyncio.run(run_test())


def test_running_cancel_signals_worker_before_terminal_state(client, current_user) -> None:
    async def run_test() -> None:
        async with SessionLocal() as session:
            run = ResearchRun(
                user_id=current_user["X-User-ID"], query="Cancel safely", status="running"
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)

            returned = await cancel_run(session, run)
            assert returned.status == "running"
            assert returned.run_data["cancellation_requested"] is True

            publisher = RunEventPublisher(session, returned)
            with pytest.raises(ResearchCancelled):
                await publisher.append("research.progress", {"status": "still_running"})

            events = list((await session.scalars(
                select(ResearchRunEvent).where(ResearchRunEvent.run_id == run.id)
            )).all())
            assert [event.event_type for event in events] == ["research.cancellation_requested"]

    asyncio.run(run_test())
