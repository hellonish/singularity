"""Non-blocking execution boundary for incremental chat summaries."""
from __future__ import annotations

import asyncio

from api.database import SessionLocal
from api.models import ChatSummary
from api.services.chats import get_chat
from api.services.summarizer import Summarizer, SummaryGenerator
from api.storage.base import ObjectStore


class SummaryScheduler:
    """Run the future specialized summary skill outside the response lifecycle."""

    def __init__(self, *, generator: SummaryGenerator, store: ObjectStore) -> None:
        self._generator = generator
        self._store = store
        self._tasks: set[asyncio.Task[ChatSummary | None]] = set()

    def schedule(
        self,
        *,
        user_id: str,
        chat_id: str,
        model_id: str,
        context_window: int,
        reserved_output_tokens: int,
    ) -> asyncio.Task[ChatSummary | None]:
        task = asyncio.create_task(
            self.run_once(
                user_id=user_id,
                chat_id=chat_id,
                model_id=model_id,
                context_window=context_window,
                reserved_output_tokens=reserved_output_tokens,
            )
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def run_once(
        self,
        *,
        user_id: str,
        chat_id: str,
        model_id: str,
        context_window: int,
        reserved_output_tokens: int,
    ) -> ChatSummary | None:
        async with SessionLocal() as session:
            chat = await get_chat(session, user_id, chat_id)
            return await Summarizer(session=session, store=self._store).summarize_if_needed(
                chat=chat,
                model_id=model_id,
                context_window=context_window,
                reserved_output_tokens=reserved_output_tokens,
                generator=self._generator,
            )
