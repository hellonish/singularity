"""Threads / Chat API router — conversation management and streaming responses."""
from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.debug_research_mock_policy import assert_debug_mock_request_allowed
from api.deps import get_current_user, get_db
from api.llm_credentials_service import (
    require_provider_key_for_model,
    validate_model_id,
)
from api.threads.schemas import (
    CreateThreadRequest,
    MessageResponse,
    PatchThreadRequest,
    SendMessageRequest,
    ThreadResponse,
    ThreadSummaryResponse,
    ThreadWithMessages,
)
from api.threads.debug_mock_research_stream import iter_debug_mock_research_sse
from api.threads.service import (
    assemble_context,
    create_thread,
    delete_thread,
    get_messages,
    get_thread,
    list_threads_with_meta,
    save_message,
    update_thread_pin,
)
from db.models import User

router = APIRouter(prefix="/threads", tags=["threads"])


def _thread_to_response(t) -> ThreadResponse:
    return ThreadResponse(
        id=t.id,
        report_id=t.report_id,
        pinned_version_num=t.pinned_version_num,
        canonical_report_qa=bool(getattr(t, "canonical_report_qa", False)),
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


@router.get("", response_model=list[ThreadSummaryResponse])
async def list_user_threads(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ThreadSummaryResponse]:
    """List the current user's threads (last activity first, with report title and preview)."""
    rows = await list_threads_with_meta(db, current_user.id, limit)
    out: list[ThreadSummaryResponse] = []
    for thread, report_title, preview, last_at, report_query, first_user_preview in rows:
        base = _thread_to_response(thread)
        out.append(
            ThreadSummaryResponse(
                **base.model_dump(),
                report_title=report_title,
                report_query=report_query,
                last_message_at=last_at,
                last_message_preview=preview,
                first_user_message_preview=first_user_preview,
            )
        )
    return out


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


@router.patch("/{thread_id}", response_model=ThreadResponse)
async def patch_thread(
    thread_id: uuid.UUID,
    body: PatchThreadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ThreadResponse:
    """Update thread settings (e.g. pinned report version for Q&A context)."""
    thread = await update_thread_pin(
        db, thread_id, current_user.id, body.pinned_version_num
    )
    return _thread_to_response(thread)


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

    if body.debug_mock and body.execution_mode != "research":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="debug_mock is only valid when execution_mode is research",
        )
    if body.debug_mock:
        assert_debug_mock_request_allowed(current_user, True)

    # Save the user's message
    await save_message(db, thread_id, "user", body.content)

    # Assemble context (history + report content if linked)
    messages, _report_md = await assemble_context(db, thread)

    # Add the user's new message to the history
    messages.append({"role": "user", "content": body.content})

    async def event_generator() -> AsyncGenerator[bytes, None]:
        assistant_content = ""
        try:
            if body.execution_mode == "research" and body.debug_mock:
                async for chunk in iter_debug_mock_research_sse(
                    db,
                    thread_id,
                    body.research_strength,
                    body.content,
                ):
                    yield chunk
                return

            from agents.chat.agent import ChatAgent

            mid = validate_model_id(body.model_id)
            api_key = await require_provider_key_for_model(db, current_user.id, mid)
            agent = ChatAgent(
                model_id=mid,
                api_key=api_key,
            )
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
                saved = await save_message(
                    db, thread_id, "assistant", assistant_content
                )
                done_payload = {
                    "message_id": str(saved.id),
                    "token_count": saved.token_count,
                }
            else:
                done_payload = {}
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n".encode()

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
