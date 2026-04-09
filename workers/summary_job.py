"""
ARQ worker task — generates a rolling summary for a chat thread.

When a thread accumulates many messages, the context window can become
too large for the LLM. This worker periodically summarizes older messages
so the thread context stays manageable while retaining key information.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Message, Thread
from api.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Number of messages after which to trigger a summary
_SUMMARY_THRESHOLD = 40

# Number of recent messages to keep unsummarized
_KEEP_RECENT = 10


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def run_summary_job(ctx: dict, thread_id: str) -> dict:
    """
    Generate or update the rolling summary for a thread.

    Flow:
    1. Load the thread and its messages
    2. Identify messages that haven't been summarized yet
    3. If enough messages (> threshold), summarize them via LLM
    4. Store the summary and mark the boundary message
    5. Return summary stats

    The summary is stored in thread.summary and the boundary is tracked
    via thread.summary_through_message_id.
    """
    async with AsyncSessionLocal() as db:
        # Load thread
        result = await db.execute(
            select(Thread).where(Thread.id == uuid.UUID(thread_id))
        )
        thread: Thread | None = result.scalar_one_or_none()
        if thread is None:
            raise ValueError(f"Thread {thread_id} not found")

        # Load all messages
        msg_result = await db.execute(
            select(Message)
            .where(Message.thread_id == thread.id)
            .order_by(Message.created_at.asc())
        )
        messages = list(msg_result.scalars().all())

        if len(messages) == 0:
            return {"status": "no_messages", "thread_id": thread_id}

        # Find the boundary: messages after the last summarized one
        boundary_idx = 0
        if thread.summary_through_message_id:
            for i, m in enumerate(messages):
                if m.id == thread.summary_through_message_id:
                    boundary_idx = i + 1
                    break

        # Messages to summarize (old ones, excluding the most recent)
        to_summarize = messages[boundary_idx:len(messages) - _KEEP_RECENT]

        if len(to_summarize) < _SUMMARY_THRESHOLD // 2:
            logger.info(
                "Thread %s: not enough messages to summarize (%d since last summary)",
                thread_id, len(to_summarize),
            )
            return {
                "status": "skipped",
                "thread_id": thread_id,
                "messages_since_last": len(to_summarize),
            }

        # Build conversation text for summarization
        conversation_text = ""
        if thread.summary:
            conversation_text = f"[Previous summary]\n{thread.summary}\n\n[New messages]\n"

        for m in to_summarize:
            role = m.role.upper()
            content_preview = m.content[:500]
            conversation_text += f"{role}: {content_preview}\n\n"

        # Call LLM for summarization (BYOK: thread owner's xAI key only)
        try:
            from api.llm_credentials_service import get_decrypted_provider_key
            from llm.router import get_llm_client

            grok_key = await get_decrypted_provider_key(db, thread.user_id, "grok")
            if not grok_key:
                logger.info(
                    "Thread %s: skip summary — user has no xAI API key (BYOK)",
                    thread_id,
                )
                return {
                    "status": "skipped_no_byok",
                    "thread_id": thread_id,
                }

            client = get_llm_client("grok-3-mini", grok_key)
            system_prompt = (
                "You are summarizing a conversation thread. "
                "Produce a concise summary that captures:\n"
                "1. The main topics discussed\n"
                "2. Key findings or conclusions\n"
                "3. Any action items or follow-ups mentioned\n"
                "Keep the summary under 500 words. "
                "Write in third person, past tense."
            )

            def _summarize_sync() -> str:
                return client.generate_text(
                    prompt=f"Summarize this conversation:\n\n{conversation_text}",
                    system_prompt=system_prompt,
                    temperature=0.2,
                    max_tokens=1000,
                )

            new_summary = (await asyncio.to_thread(_summarize_sync)).strip()

            # Find the last message we summarized
            last_summarized = to_summarize[-1]

            thread.summary = new_summary
            thread.summary_through_message_id = last_summarized.id
            await db.commit()

            logger.info(
                "Thread %s summarized: %d messages summarized, summary length: %d",
                thread_id, len(to_summarize), len(new_summary),
            )

            return {
                "status": "summarized",
                "thread_id": thread_id,
                "messages_summarized": len(to_summarize),
                "summary_length": len(new_summary),
            }

        except Exception as exc:
            logger.error("Summary job failed for thread %s: %s", thread_id, exc)
            raise
