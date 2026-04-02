"""Threads / Chat API router — conversation management and streaming responses."""
from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.threads.schemas import (
    CreateThreadRequest,
    MessageResponse,
    SendMessageRequest,
    ThreadResponse,
    ThreadWithMessages,
)
from api.threads.service import (
    assemble_context,
    create_thread,
    delete_thread,
    get_messages,
    get_thread,
    list_threads,
    save_message,
)
from db.models import User

router = APIRouter(prefix="/threads", tags=["threads"])


def _thread_to_response(t) -> ThreadResponse:
    return ThreadResponse(
        id=t.id,
        report_id=t.report_id,
        pinned_version_num=t.pinned_version_num,
        created_at=t.created_at,
    )


def _message_to_response(m) -> MessageResponse:
    return MessageResponse(
        id=m.id,
        role=m.role,
        content=m.content,
        token_count=m.token_count,
        created_at=m.created_at,
    )


@router.post("", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_new_thread(
    body: CreateThreadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadResponse:
    """Create a new chat thread, optionally linked to a report."""
    thread = await create_thread(
        db,
        current_user.id,
        body.report_id,
        body.pinned_version,
    )
    return _thread_to_response(thread)


@router.get("", response_model=list[ThreadResponse])
async def list_user_threads(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ThreadResponse]:
    """List the current user's threads."""
    threads = await list_threads(db, current_user.id, limit)
    return [_thread_to_response(t) for t in threads]


@router.get("/{thread_id}", response_model=ThreadWithMessages)
async def get_thread_detail(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadWithMessages:
    """Get a thread with all its messages."""
    thread = await get_thread(db, thread_id, current_user.id)
    messages = await get_messages(db, thread_id)
    return ThreadWithMessages(
        thread=_thread_to_response(thread),
        messages=[_message_to_response(m) for m in messages],
    )


@router.delete("/{thread_id}", status_code=status.HTTP_200_OK)
async def delete_user_thread(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a thread and all its messages."""
    await delete_thread(db, thread_id, current_user.id)
    return {"status": "deleted"}


@router.post("/{thread_id}/messages")
async def send_message(
    thread_id: uuid.UUID,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Send a message and receive a streaming response (SSE).

    The response streams events: plan, step_start, token, step_end, done, error.
    """
    thread = await get_thread(db, thread_id, current_user.id)

    # Save the user's message
    await save_message(db, thread_id, "user", body.content)

    # Assemble context (history + report content if linked)
    messages, _report_md = await assemble_context(db, thread)

    # Add the user's new message to the history
    messages.append({"role": "user", "content": body.content})

    async def event_generator() -> AsyncGenerator[bytes, None]:
        assistant_content = ""
        try:
            from agents.chat.agent import ChatAgent

            agent = ChatAgent()
            async for item in agent.stream_turn(
                body.content,
                messages[:-1],
                execution_mode=body.execution_mode,
                chat_variant=body.chat_variant,
                research_strength=body.research_strength,
            ):
                if isinstance(item, dict) and item.get("kind") == "plan":
                    payload = json.dumps(item.get("plan", {}))
                    yield f"event: plan\ndata: {payload}\n\n".encode()
                elif isinstance(item, dict) and item.get("kind") == "step":
                    payload = json.dumps({
                        "step_id": item.get("step_id"),
                        "step_type": item.get("step_type"),
                        "description": item.get("description"),
                    })
                    yield f"event: step\ndata: {payload}\n\n".encode()
                elif isinstance(item, str):
                    assistant_content += item
                    data = json.dumps({"token": item})
                    yield f"event: token\ndata: {data}\n\n".encode()

            if assistant_content:
                await save_message(db, thread_id, "assistant", assistant_content)

            yield f"event: done\ndata: {{}}\n\n".encode()

        except Exception as e:
            error_data = json.dumps({"message": str(e)})
            yield f"event: error\ndata: {error_data}\n\n".encode()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
