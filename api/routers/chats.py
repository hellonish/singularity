from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from api.dependencies import CurrentUserDep, SessionDep
from api.config import settings
from api.schemas import (
    ChatCreate,
    ChatRead,
    ChatSummaryCreate,
    ChatSummaryRead,
    ChatUpdate,
    MessageCreate,
    MessageRead,
)
from api.services import chats as chat_service
from api.sse import SSE_HEADERS, encode_sse

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=list[ChatRead])
async def list_chats(session: SessionDep, current_user: CurrentUserDep) -> list[ChatRead]:
    return await chat_service.list_chats(session, current_user.id)


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
async def create_chat(
    body: ChatCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ChatRead:
    return await chat_service.create_chat(session, current_user, body)


@router.get("/{chat_id}", response_model=ChatRead)
async def get_chat(chat_id: str, session: SessionDep, current_user: CurrentUserDep) -> ChatRead:
    return await chat_service.get_chat(session, current_user.id, chat_id)


@router.patch("/{chat_id}", response_model=ChatRead)
async def update_chat(
    chat_id: str,
    body: ChatUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ChatRead:
    chat = await chat_service.get_chat(session, current_user.id, chat_id)
    return await chat_service.update_chat(session, chat, body)


@router.delete("/{chat_id}", response_model=ChatRead)
async def archive_chat(chat_id: str, session: SessionDep, current_user: CurrentUserDep) -> ChatRead:
    chat = await chat_service.get_chat(session, current_user.id, chat_id)
    return await chat_service.update_chat(session, chat, ChatUpdate(status="archived"))


@router.get("/{chat_id}/messages", response_model=list[MessageRead])
async def list_messages(chat_id: str, session: SessionDep, current_user: CurrentUserDep) -> list[MessageRead]:
    chat = await chat_service.get_chat(session, current_user.id, chat_id)
    return await chat_service.list_messages(session, chat)


@router.post("/{chat_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def create_message(
    chat_id: str,
    body: MessageCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> MessageRead:
    chat = await chat_service.get_chat(session, current_user.id, chat_id)
    return await chat_service.create_message(session, chat, body)


@router.post("/{chat_id}/messages/stream")
async def stream_message(
    chat_id: str,
    body: MessageCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    """Stream a deterministic dummy reply through the backend SSE contract."""

    chat = await chat_service.get_chat(session, current_user.id, chat_id)
    message = await chat_service.create_message(session, chat, body)
    chunks = ("This is ", "a dummy streamed ", "chat response.")

    async def events() -> AsyncIterator[str]:
        yield encode_sse(
            event="message.accepted",
            event_id=f"{message.id}:0",
            data={"chat_id": chat.id, "message_id": message.id},
        )
        content = ""
        for index, chunk in enumerate(chunks, start=1):
            if settings.sse_dummy_delay_seconds:
                await asyncio.sleep(settings.sse_dummy_delay_seconds)
            content += chunk
            yield encode_sse(
                event="message.delta",
                event_id=f"{message.id}:{index}",
                data={"message_id": message.id, "index": index - 1, "delta": chunk},
            )
        yield encode_sse(
            event="message.completed",
            event_id=f"{message.id}:{len(chunks) + 1}",
            data={"message_id": message.id, "content": content},
        )

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/{chat_id}/summaries", response_model=list[ChatSummaryRead])
async def list_summaries(chat_id: str, session: SessionDep, current_user: CurrentUserDep) -> list[ChatSummaryRead]:
    chat = await chat_service.get_chat(session, current_user.id, chat_id)
    return await chat_service.list_summaries(session, chat)


@router.post("/{chat_id}/summaries", response_model=ChatSummaryRead, status_code=status.HTTP_201_CREATED)
async def create_summary(
    chat_id: str,
    body: ChatSummaryCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ChatSummaryRead:
    chat = await chat_service.get_chat(session, current_user.id, chat_id)
    return await chat_service.create_summary(session, chat, body)
