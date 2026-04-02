"""Pydantic schemas for the Reports API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Report list / meta
# ---------------------------------------------------------------------------

class ReportMeta(BaseModel):
    id: UUID
    title: Optional[str]
    query: str
    strength: int
    created_at: datetime
    latest_version: Optional[int] = None
    latest_char_count: Optional[int] = None

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportMeta]
    next_cursor: Optional[str] = None


# ---------------------------------------------------------------------------
# Report versions
# ---------------------------------------------------------------------------

class VersionMeta(BaseModel):
    version_num: int
    char_count: int
    patch_instruction: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionListResponse(BaseModel):
    report_id: UUID
    versions: list[VersionMeta]


class VersionContent(BaseModel):
    version_num: int
    content: str
    etag: str  # SHA-256 content hash
    char_count: int


# ---------------------------------------------------------------------------
# Patch request
# ---------------------------------------------------------------------------

class PatchRequest(BaseModel):
    selected_text: str = Field(..., min_length=1, max_length=50000)
    instruction: str = Field(..., min_length=1, max_length=2000)
    if_match: str  # ETag for optimistic locking


class PatchResponse(BaseModel):
    new_version_num: int
    etag: str
    char_count: int
