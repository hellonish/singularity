from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from api.dependencies import CurrentUserDep, SessionDep
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
from api.services.chat_stream import build_stream, generate_chat_title
from api.services.report_context_errors import ReportContextError
from api.sse import SSE_HEADERS, encode_sse
from engine.llm.groq import GroqProviderError

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
    """Stream a real engine chat reply through the backend SSE contract.

    The user message is persisted, the engine ChatAgent streams live deltas,
    and the assistant reply is persisted before the stream closes so
    ``GET /chats/{id}/messages`` returns the full turn. Provider failures are
    surfaced as a terminal ``message.error`` event rather than a torn stream.
    """

    chat = await chat_service.get_chat(session, current_user.id, chat_id)
    user_message = await chat_service.create_message(session, chat, body)

    # Resolve the credential and open the engine stream before returning a
    # StreamingResponse. A missing credential raises HTTPException(422) here, so
    # the caller receives a normal error response instead of an SSE stream.
    #
    # A report-linked chat also loads report context here. If the vector store
    # is unavailable that raises ReportContextError: rather than answering
    # without the report (which would be confidently wrong), we open the stream
    # and emit a single terminal ``message.error`` with a generic load message,
    # matching how downstream provider failures already surface.
    try:
        stream, config = await build_stream(session, chat, user_message)
    except ReportContextError as exc:
        # Bind the fields now: ``exc`` is unbound once this except block exits,
        # and the generator below runs lazily inside the StreamingResponse.
        error_payload = {
            "message_id": user_message.id,
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
        }

        async def context_error() -> AsyncIterator[str]:
            yield encode_sse(
                event="message.error",
                event_id=f"{user_message.id}:1",
                data=error_payload,
            )

        return StreamingResponse(context_error(), media_type="text/event-stream", headers=SSE_HEADERS)

    async def events() -> AsyncIterator[str]:
        index = 0
        content = ""
        try:
            async for event in stream:
                if event.type == "started":
                    yield encode_sse(
                        event="message.accepted",
                        event_id=f"{user_message.id}:{index}",
                        data={
                            "chat_id": chat.id,
                            "message_id": user_message.id,
                            "model_id": event.model_id,
                        },
                    )
                elif event.type == "delta":
                    index += 1
                    content += event.delta or ""
                    yield encode_sse(
                        event="message.delta",
                        event_id=f"{user_message.id}:{index}",
                        data={"message_id": user_message.id, "index": index - 1, "delta": event.delta or ""},
                    )
                elif event.type == "completed":
                    index += 1
                    final = event.content or content
                    assistant = await chat_service.create_message(
                        session,
                        chat,
                        MessageCreate(content=final, role="assistant", parent_message_id=user_message.id),
                    )
                    yield encode_sse(
                        event="message.completed",
                        event_id=f"{user_message.id}:{index}",
                        data={
                            "message_id": user_message.id,
                            "assistant_message_id": assistant.id,
                            "content": final,
                        },
                    )
                    # First completed turn of an untitled chat: name it from the
                    # exchange. generate_chat_title never raises (it falls back
                    # to an excerpt of the user message), so a title problem can
                    # never invalidate the already-delivered reply.
                    if not chat.title:
                        title = await generate_chat_title(session, chat, user_message.content, final)
                        index += 1
                        yield encode_sse(
                            event="chat.title",
                            event_id=f"{user_message.id}:{index}",
                            data={"chat_id": chat.id, "title": title},
                        )
        except GroqProviderError as exc:
            index += 1
            yield encode_sse(
                event="message.error",
                event_id=f"{user_message.id}:{index}",
                data={
                    "message_id": user_message.id,
                    "code": exc.code,
                    "message": exc.message,
                    "retryable": exc.retryable,
                },
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
