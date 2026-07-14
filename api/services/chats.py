from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Chat, ChatSummary, LLMProviderCredential, Message, Report, User
from api.schemas import ChatCreate, ChatSummaryCreate, ChatUpdate, MessageCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_chat(session: AsyncSession, user_id: str, chat_id: str) -> Chat:
    result = await session.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id))
    chat = result.scalar_one_or_none()
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat


async def list_chats(session: AsyncSession, user_id: str) -> list[Chat]:
    result = await session.execute(
        select(Chat)
        .where(Chat.user_id == user_id, Chat.status != "archived")
        .order_by(Chat.last_message_at.desc(), Chat.created_at.desc())
    )
    return list(result.scalars())


async def create_chat(session: AsyncSession, user: User, body: ChatCreate) -> Chat:
    if body.report_id is not None:
        report = await session.get(Report, body.report_id)
        if report is None or report.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    credential = await _get_owned_credential(session, user.id, body.provider_credential_id)
    selected_model = body.model_id if body.model_id is not None else body.model_name
    chat = Chat(
        user_id=user.id,
        report_id=body.report_id,
        title=body.title,
        provider_credential_id=credential.id if credential else None,
        model_provider=credential.provider if credential else body.model_provider,
        model_name=selected_model,
    )
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


async def update_chat(session: AsyncSession, chat: Chat, body: ChatUpdate) -> Chat:
    if body.title is not None:
        chat.title = body.title
    if body.status is not None:
        chat.status = body.status
    if "report_id" in body.model_fields_set:
        if body.report_id is not None:
            report = await session.get(Report, body.report_id)
            if report is None or report.user_id != chat.user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        chat.report_id = body.report_id
    if "provider_credential_id" in body.model_fields_set:
        credential = await _get_owned_credential(session, chat.user_id, body.provider_credential_id)
        chat.provider_credential_id = credential.id if credential else None
        chat.model_provider = credential.provider if credential else None
    if "model_id" in body.model_fields_set:
        chat.model_name = body.model_id
    await session.commit()
    await session.refresh(chat)
    return chat


async def _get_owned_credential(
    session: AsyncSession,
    user_id: str,
    credential_id: str | None,
) -> LLMProviderCredential | None:
    if credential_id is None:
        return None
    credential = await session.get(LLMProviderCredential, credential_id)
    if credential is None or credential.user_id != user_id or credential.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider credential not found")
    return credential


async def list_messages(session: AsyncSession, chat: Chat) -> list[Message]:
    result = await session.execute(select(Message).where(Message.chat_id == chat.id).order_by(Message.sequence))
    return list(result.scalars())


async def create_message(session: AsyncSession, chat: Chat, body: MessageCreate) -> Message:
    last_sequence = await session.scalar(
        select(func.coalesce(func.max(Message.sequence), 0)).where(Message.chat_id == chat.id)
    )
    message = Message(
        chat_id=chat.id,
        sequence=int(last_sequence or 0) + 1,
        role=body.role,
        content=body.content,
        parent_message_id=body.parent_message_id,
        message_data=body.message_data,
    )
    # Bump recency with an UPDATE rather than mutating ``chat``: streaming
    # callers persist the assistant turn after the request scope closed, where
    # ``chat`` is detached and an attribute write would be silently dropped.
    now = _now()
    await session.execute(sql_update(Chat).where(Chat.id == chat.id).values(last_message_at=now))
    chat.last_message_at = now
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def list_summaries(session: AsyncSession, chat: Chat) -> list[ChatSummary]:
    result = await session.execute(
        select(ChatSummary).where(ChatSummary.chat_id == chat.id).order_by(ChatSummary.sequence)
    )
    return list(result.scalars())


async def create_summary(session: AsyncSession, chat: Chat, body: ChatSummaryCreate) -> ChatSummary:
    last_sequence = await session.scalar(
        select(func.coalesce(func.max(ChatSummary.sequence), 0)).where(ChatSummary.chat_id == chat.id)
    )
    summary = ChatSummary(
        chat_id=chat.id,
        sequence=int(last_sequence or 0) + 1,
        content=body.content,
        through_message_id=body.through_message_id,
        token_count=body.token_count,
        summary_data=body.summary_data,
    )
    session.add(summary)
    await session.commit()
    await session.refresh(summary)
    return summary
