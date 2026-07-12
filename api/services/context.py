"""Load the persisted context required for one chat response."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Chat, ChatSummary, Message, Report, ReportVersion
from api.services.reports import read_version_content
from api.storage.base import ObjectStore
from engine.chat.context import ContextSnapshot, ContextTurn, ReportContext, SummaryContext


class ContextManager:
    """Build a role-preserving snapshot from chat, report, and summary state."""

    def __init__(self, *, session: AsyncSession, store: ObjectStore) -> None:
        self._session = session
        self._store = store

    async def build(self, chat: Chat) -> ContextSnapshot:
        summary, through_sequence = await self._load_latest_summary(chat.id)
        turns = await self._load_turns_after(chat.id, through_sequence)
        report = await self._load_report_context(chat)
        return ContextSnapshot(
            chat_id=chat.id,
            report=report,
            summary=summary,
            turns=turns,
            latest_message_id=turns[-1].id if turns else None,
        )

    async def _load_latest_summary(self, chat_id: str) -> tuple[SummaryContext | None, int]:
        summary = await self._session.scalar(
            select(ChatSummary)
            .where(ChatSummary.chat_id == chat_id)
            .order_by(ChatSummary.sequence.desc())
            .limit(1)
        )
        if summary is None:
            return None, 0

        through_sequence = 0
        if summary.through_message_id is not None:
            through_sequence = int(
                await self._session.scalar(
                    select(Message.sequence).where(
                        Message.id == summary.through_message_id,
                        Message.chat_id == chat_id,
                    )
                )
                or 0
            )
        return (
            SummaryContext(
                id=summary.id,
                sequence=summary.sequence,
                through_message_id=summary.through_message_id,
                through_message_sequence=through_sequence,
                content=summary.content,
                token_count=summary.token_count,
            ),
            through_sequence,
        )

    async def _load_turns_after(self, chat_id: str, sequence: int) -> tuple[ContextTurn, ...]:
        result = await self._session.execute(
            select(Message)
            .where(Message.chat_id == chat_id, Message.sequence > sequence)
            .order_by(Message.sequence)
        )
        return tuple(
            ContextTurn(id=message.id, sequence=message.sequence, role=message.role, content=message.content)
            for message in result.scalars()
        )

    async def _load_report_context(self, chat: Chat) -> ReportContext | None:
        if chat.report_id is None:
            return None
        report = await self._session.scalar(
            select(Report).where(Report.id == chat.report_id, Report.user_id == chat.user_id)
        )
        if report is None:
            return None
        versions = await self._session.execute(
            select(ReportVersion)
            .where(ReportVersion.report_id == report.id)
            .order_by(ReportVersion.version_number.desc())
        )
        for version in versions.scalars():
            try:
                content = await read_version_content(version, self._store)
            except HTTPException as exc:
                # A newer object can be unavailable while an older committed
                # report remains readable; select the newest readable version.
                if exc.status_code == status.HTTP_404_NOT_FOUND:
                    continue
                raise
            return ReportContext(
                report_id=report.id,
                version_id=version.id,
                version_number=version.version_number,
                checksum=version.checksum,
                content=content,
            )
        return None
