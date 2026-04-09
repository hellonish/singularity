"""
API request/response models (Pydantic), colocated under the database package.

Import from here or from submodules, e.g. ``from api.db.schemas import JobResponse``.
"""
from __future__ import annotations

from api.db.schemas.auth import GoogleAuthRequest, RefreshRequest, TokenPair
from api.db.schemas.reports import (
    PatchRequest,
    PatchResponse,
    ReportListResponse,
    ReportMeta,
    VersionContent,
    VersionListResponse,
    VersionMeta,
)
from api.db.schemas.research import CreateJobRequest, JobResponse
from api.db.schemas.threads import (
    CreateThreadRequest,
    MessageResponse,
    PatchThreadRequest,
    SendMessageRequest,
    ThreadResponse,
    ThreadSummaryResponse,
    ThreadWithMessages,
)
from api.db.schemas.users import (
    BrowserBreakdownItem,
    DeviceBreakdownItem,
    DeviceBreakdownResponse,
    LlmCredentialDeleteResponse,
    LlmCredentialListResponse,
    LlmCredentialPublic,
    LlmCredentialPutBody,
    ModelBreakdownItem,
    ModelBreakdownResponse,
    OSBreakdownItem,
    UsageSeriesPoint,
    UsageSeriesResponse,
    UsageStats,
    UserProfile,
)

__all__ = [
    "BrowserBreakdownItem",
    "CreateJobRequest",
    "CreateThreadRequest",
    "DeviceBreakdownItem",
    "DeviceBreakdownResponse",
    "GoogleAuthRequest",
    "JobResponse",
    "LlmCredentialDeleteResponse",
    "LlmCredentialListResponse",
    "LlmCredentialPublic",
    "LlmCredentialPutBody",
    "MessageResponse",
    "ModelBreakdownItem",
    "ModelBreakdownResponse",
    "OSBreakdownItem",
    "PatchRequest",
    "PatchResponse",
    "PatchThreadRequest",
    "RefreshRequest",
    "ReportListResponse",
    "ReportMeta",
    "SendMessageRequest",
    "ThreadResponse",
    "ThreadSummaryResponse",
    "ThreadWithMessages",
    "TokenPair",
    "UsageSeriesPoint",
    "UsageSeriesResponse",
    "UsageStats",
    "UserProfile",
    "VersionContent",
    "VersionListResponse",
    "VersionMeta",
]
