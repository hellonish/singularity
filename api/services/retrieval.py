"""Authorization-first retrieval facade for chat and report context."""
from __future__ import annotations

from typing import Literal, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from api.services.chats import get_chat
from api.services.reports import get_report
from vector_store import DocumentChunk, RetrievalScope


class TenantVectorStore(Protocol):
    def search(
        self,
        *,
        scope: RetrievalScope,
        query_text: str,
        limit: int = 8,
        min_credibility: float = 0.0,
    ) -> list[DocumentChunk]: ...


class RetrievalService:
    """Construct vector scopes only after relational ownership checks."""

    def __init__(self, *, session: AsyncSession, vector_store: TenantVectorStore) -> None:
        self._session = session
        self._vector_store = vector_store

    async def search_chat(
        self,
        *,
        user_id: str,
        chat_id: str,
        query: str,
        limit: int = 8,
    ) -> list[DocumentChunk]:
        chat = await get_chat(self._session, user_id, chat_id)
        return self._vector_store.search(
            scope=RetrievalScope(user_id=user_id, conversation_id=chat.id),
            query_text=query,
            limit=limit,
        )

    async def search_report(
        self,
        *,
        user_id: str,
        report_id: str,
        query: str,
        limit: int = 8,
    ) -> list[DocumentChunk]:
        report = await get_report(self._session, user_id, report_id)
        return self._vector_store.search(
            scope=RetrievalScope(user_id=user_id, report_id=report.id),
            query_text=query,
            limit=limit,
        )

    async def search_authorized_resource(
        self,
        *,
        user_id: str,
        resource_type: Literal["chat", "report"],
        resource_id: str,
        query: str,
        limit: int = 8,
    ) -> list[DocumentChunk]:
        """API-only entrypoint used by the production retrieval skill."""
        if resource_type == "chat":
            return await self.search_chat(user_id=user_id, chat_id=resource_id, query=query, limit=limit)
        return await self.search_report(user_id=user_id, report_id=resource_id, query=query, limit=limit)
