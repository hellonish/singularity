"""Pydantic schemas for the Threads / Chat API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, Field


class CreateThreadRequest(BaseModel):
    report_id: Optional[UUID] = None
    pinned_version: Optional[int] = None


class ThreadResponse(BaseModel):
    id: UUID
    report_id: Optional[UUID]
    pinned_version_num: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


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
    research_strength: int = Field(5, ge=1, le=10)
    """When execution_mode is research: pipeline strength passed to run_pipeline."""
