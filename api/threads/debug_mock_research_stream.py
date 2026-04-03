"""
SSE byte chunks for debug mock chat research (no ChatAgent / run_pipeline).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from api.threads.service import save_message

_MOCK_ASSISTANT_MARKDOWN = """# Mock research response

This answer is streamed from the **debug mock** path (no LLM).

## Section

- Item one (integration test)
- Item two

### Math

Inline: $E = mc^2$.

> End of mock template.
"""


async def iter_debug_mock_research_sse(
    db: AsyncSession,
    thread_id: uuid.UUID,
    research_strength: int,
    user_query: str,
) -> AsyncGenerator[bytes, None]:
    """
    Yields SSE lines: plan, step (several), token chunks, then persists assistant
    message and yields done with message_id.
    """
    plan = {
        "mode": "research",
        "reasoning": "Debug mock plan — no real thinker or pipeline.",
        "selected_skills": ["web_search", "academic_search"],
        "strength": research_strength,
        "audience": "practitioner",
        "steps": [
            {
                "step_id": 1,
                "type": "web_search",
                "description": "Background scan (mock)",
                "skill_name": None,
            },
            {
                "step_id": 2,
                "type": "skill_call",
                "description": "Academic sources (mock)",
                "skill_name": "academic_search",
            },
            {
                "step_id": 3,
                "type": "synthesis",
                "description": "Merge findings (mock)",
                "skill_name": None,
            },
        ],
    }
    yield f"event: plan\ndata: {json.dumps(plan)}\n\n".encode()

    mock_steps = [
        (1, "web_search", "Resolving query in mock layer…"),
        (2, "skill_call", "Consulting academic_search (mock)…"),
        (3, "synthesis", "Streaming synthetic markdown…"),
    ]
    for step_id, step_type, desc in mock_steps:
        await asyncio.sleep(0.08)
        payload = json.dumps(
            {"step_id": step_id, "step_type": step_type, "description": desc}
        )
        yield f"event: step\ndata: {payload}\n\n".encode()

    text = (
        _MOCK_ASSISTANT_MARKDOWN
        + "\n\n---\n\n*Debug mock — query excerpt:* "
        + json.dumps(user_query[:300])
        + "\n"
    )
    chunk_size = 48
    for i in range(0, len(text), chunk_size):
        await asyncio.sleep(0.04)
        piece = text[i : i + chunk_size]
        yield f"event: token\ndata: {json.dumps({'token': piece})}\n\n".encode()

    msg = await save_message(
        db,
        thread_id,
        "assistant",
        text,
        token_count=max(1, len(text) // 4),
    )
    done_payload = {
        "message_id": str(msg.id),
        "token_count": msg.token_count,
    }
    yield f"event: done\ndata: {json.dumps(done_payload)}\n\n".encode()
