from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateJobRequest(BaseModel):
    query: str = Field(..., min_length=10, max_length=2000)
    strength: int = Field(5, ge=1, le=10)
    idempotency_key: Optional[str] = None


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
