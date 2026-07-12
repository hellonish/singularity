"""Incremental, immutable chat-summary orchestration."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Chat, ChatSummary
from api.schemas import ChatSummaryCreate
from api.services.chats import create_summary
from api.services.context import ContextManager
from api.storage.base import ObjectStore
from engine.chat.budget import TokenCounter
from engine.chat.context import ContextTurn, UniversalContextPolicy


@dataclass(frozen=True)
class GeneratedSummary:
    content: str
    token_count: int | None = None
    metadata: dict[str, Any] | None = None


class SummaryGenerator(Protocol):
    """Implemented later by the specialized summary-quality skill."""

    async def summarize(
        self,
        *,
        previous_summary: str | None,
        turns: tuple[ContextTurn, ...],
        max_output_tokens: int,
    ) -> GeneratedSummary: ...


class Summarizer:
    """Create one new summary only after completed turns cross the threshold."""

    _locks: dict[str, asyncio.Lock] = {}

    def __init__(
        self,
        *,
        session: AsyncSession,
        store: ObjectStore,
        policy: UniversalContextPolicy | None = None,
    ) -> None:
        self._session = session
        self._store = store
        self._policy = policy or UniversalContextPolicy()

    async def summarize_if_needed(
        self,
        *,
        chat: Chat,
        model_id: str,
        context_window: int,
        reserved_output_tokens: int,
        generator: SummaryGenerator,
    ) -> ChatSummary | None:
        snapshot = await ContextManager(session=self._session, store=self._store).build(chat)
        if not snapshot.turns or snapshot.turns[-1].role != "assistant":
            return None

        counter = TokenCounter(model_id)
        source_token_count = sum(counter.count(turn.role) + counter.count(turn.content) for turn in snapshot.turns)
        threshold = self._policy.summary_trigger_tokens(
            context_window=context_window,
            reserved_output_tokens=reserved_output_tokens,
        )
        if source_token_count < threshold:
            return None

        generated = await generator.summarize(
            previous_summary=snapshot.summary.content if snapshot.summary else None,
            turns=snapshot.turns,
            max_output_tokens=self._policy.summary_output_cap_tokens(
                context_window=context_window,
                reserved_output_tokens=reserved_output_tokens,
            ),
        )
        if not generated.content.strip():
            raise ValueError("summary generator returned empty content")

        lock = self._locks.setdefault(chat.id, asyncio.Lock())
        async with lock:
            # A concurrent completion may have already advanced the immutable
            # coverage boundary while the generator was running.
            refreshed = await ContextManager(session=self._session, store=self._store).build(chat)
            if refreshed.latest_message_id != snapshot.latest_message_id:
                return None
            if (refreshed.summary.id if refreshed.summary else None) != (
                snapshot.summary.id if snapshot.summary else None
            ):
                return None

            metadata = {
                "previous_summary_id": snapshot.summary.id if snapshot.summary else None,
                "through_message_sequence": snapshot.turns[-1].sequence,
                "source_token_count": source_token_count,
                "model_id": model_id,
                "summarizer_version": (generated.metadata or {}).get("version", "pending-specialized-skill"),
                **(generated.metadata or {}),
            }
            return await create_summary(
                self._session,
                chat,
                ChatSummaryCreate(
                    content=generated.content,
                    through_message_id=snapshot.latest_message_id,
                    token_count=generated.token_count,
                    summary_data=metadata,
                ),
            )
