from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from agents.chat.models import DEFAULT_MODEL_ID


class CreateJobRequest(BaseModel):
    query: str = Field(..., min_length=10, max_length=2000)
    strength: int = Field(2, ge=1, le=3, description="1=low, 2=medium, 3=high")
    model_id: str = Field(
        default=DEFAULT_MODEL_ID,
        max_length=128,
        description="Chat-catalog model id; full pipeline uses it with the user's BYOK key for that provider.",
    )
    idempotency_key: Optional[str] = None
    debug_mock: bool = Field(
        default=False,
        description="When true with server flag + allowlisted user, run mock worker (no LLM).",
    )


class JobResponse(BaseModel):
    job_id: str
    report_id: str
    status: str
    current_phase: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_detail: Optional[str]

    model_config = {"from_attributes": True}
