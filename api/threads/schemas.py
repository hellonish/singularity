"""Pydantic schemas for the Threads / Chat API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, Field

from agents.chat.models import DEFAULT_MODEL_ID


class CreateThreadRequest(BaseModel):
    report_id: Optional[UUID] = None
    pinned_version: Optional[int] = None


class ThreadResponse(BaseModel):
    id: UUID
    report_id: Optional[UUID]
    pinned_version_num: Optional[int]
    canonical_report_qa: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadSummaryResponse(ThreadResponse):
    """Thread row for chat history lists (activity sort + report context)."""

    report_title: Optional[str] = None
    report_query: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_message_preview: Optional[str] = None
    first_user_message_preview: Optional[str] = None


class PatchThreadRequest(BaseModel):
    """Pin a specific report version for context, or null to follow latest."""

    pinned_version_num: Optional[int] = None


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    token_count: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadWithMessages(BaseModel):
    thread: ThreadResponse
    messages: list[MessageResponse]


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    execution_mode: Literal["chat", "research"] = "chat"
    """User-selected run mode: lightweight chat steps vs full research pipeline."""
    chat_variant: Literal["standard", "extended"] = "standard"
    """When execution_mode is chat: standard (1–5 style steps) vs extended thinker (deeper plans)."""
    research_strength: int = Field(2, ge=1, le=3)
    """When execution_mode is research: intensity tier (1=low, 2=medium, 3=high) for run_pipeline."""
    model_id: str = Field(default=DEFAULT_MODEL_ID, max_length=160)
    """Chat-catalog model id; thinker, chat execution, and research pipeline all use this model with BYOK."""
