"""Pydantic contracts for the API v2 domain model.

These schemas intentionally expose stable, implementation-neutral data shapes.
Routers can grow without leaking SQLAlchemy objects into the public API.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: Optional[str] = Field(default=None, max_length=320)
    display_name: Optional[str] = Field(default=None, max_length=160)
    auth_provider: Optional[str] = Field(default=None, max_length=48)
    external_subject: Optional[str] = Field(default=None, max_length=255)


class UserRead(APIModel):
    id: str
    email: Optional[str]
    display_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=160)
    status: Optional[Literal["active", "suspended"]] = None
    profile_data: Optional[dict[str, Any]] = None


class ChatCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    report_id: Optional[str] = None
    model_provider: Optional[str] = Field(default=None, max_length=48)
    model_name: Optional[str] = Field(default=None, max_length=128)
    provider_credential_id: Optional[str] = None
    model_id: Optional[str] = Field(default=None, max_length=255)


class ChatRead(APIModel):
    id: str
    user_id: str
    report_id: Optional[str]
    provider_credential_id: Optional[str]
    title: Optional[str]
    status: str
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ChatUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    status: Optional[Literal["active", "archived"]] = None
    report_id: Optional[str] = None
    provider_credential_id: Optional[str] = None
    model_id: Optional[str] = Field(default=None, max_length=255)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)
    role: Literal["system", "user", "assistant", "tool"] = "user"
    parent_message_id: Optional[str] = None
    message_data: dict[str, Any] = Field(default_factory=dict)


class MessageRead(APIModel):
    id: str
    chat_id: str
    sequence: int
    role: str
    content: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    created_at: datetime


class ChatSummaryRead(APIModel):
    id: str
    chat_id: str
    sequence: int
    content: str
    through_message_id: Optional[str]
    token_count: Optional[int]
    created_at: datetime


class ChatSummaryCreate(BaseModel):
    """Persisted summary emitted by the engine or an administrative client."""

    content: str = Field(min_length=1)
    through_message_id: Optional[str] = None
    token_count: Optional[int] = Field(default=None, ge=0)
    summary_data: dict[str, Any] = Field(default_factory=dict)


class ReportCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    source: Optional[str] = Field(default=None, max_length=64)
    report_data: dict[str, Any] = Field(default_factory=dict)


class ReportRead(APIModel):
    id: str
    user_id: str
    title: Optional[str]
    status: str
    source: Optional[str]
    created_at: datetime
    updated_at: datetime


class ReportVersionCreate(BaseModel):
    content: str = Field(min_length=1)
    content_format: str = Field(default="markdown", max_length=32)
    change_note: Optional[str] = None
    parent_version_id: Optional[str] = None
    version_data: dict[str, Any] = Field(default_factory=dict)


class ReportVersionRead(APIModel):
    id: str
    report_id: str
    version_number: int
    parent_version_id: Optional[str]
    content: Optional[str]
    content_uri: Optional[str]
    content_size_bytes: int
    content_format: str
    checksum: str
    change_note: Optional[str]
    created_at: datetime


class ResearchRunCreate(BaseModel):
    query: str = Field(min_length=1, max_length=10_000)
    title: Optional[str] = Field(default=None, max_length=500)
    report_id: Optional[str] = None
    engine_version: Optional[str] = Field(default=None, max_length=128)
    provider_credential_id: Optional[str] = None
    model_id: Optional[str] = Field(default=None, max_length=255)
    strength: int = Field(default=2, ge=1, le=3)
    audience: str = Field(default="practitioner", min_length=1, max_length=64)
    output_language: str = Field(default="en", min_length=2, max_length=12)
    # Real-inference smoke test flag. Honored only when the server enables
    # SINGULARITY_RESEARCH_TEST_MODE; ignored otherwise. Forces a single-node
    # run with one real search and one real fetch.
    test_mode: bool = False
    run_data: dict[str, Any] = Field(default_factory=dict)


class ResearchPreparationCreate(BaseModel):
    query: str = Field(min_length=10, max_length=10_000)
    provider_credential_id: str
    model_id: Optional[str] = Field(default=None, max_length=255)
    strength: int = Field(default=2, ge=1, le=3)
    approval_mode: Literal["ask", "auto"] = "ask"
    audience: str = Field(default="practitioner", min_length=1, max_length=64)
    output_language: str = Field(default="en", min_length=2, max_length=12)


class ResearchPreparationAnswerCreate(BaseModel):
    question_id: str = Field(min_length=1, max_length=80)
    answer: str = Field(min_length=1, max_length=4_000)


class ResearchPreparationRead(APIModel):
    id: str
    user_id: str
    query: str
    approval_mode: str
    status: str
    model_id: Optional[str]
    strength: int
    current_question_index: int
    plan_data: dict[str, Any]
    answers: dict[str, Any]
    final_brief: dict[str, Any]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class ResearchRunRead(APIModel):
    id: str
    user_id: str
    report_id: Optional[str]
    preparation_id: Optional[str]
    query: str
    status: str
    engine_version: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
    run_data: dict[str, Any]


class ResearchPreparationResult(BaseModel):
    preparation: ResearchPreparationRead
    run: Optional[ResearchRunRead] = None


class ResearchRunEventRead(APIModel):
    id: str
    run_id: str
    sequence: int
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class UsageRollupRead(APIModel):
    id: str
    usage_id: str
    period_kind: Literal["day", "week", "month"]
    period_start: datetime
    period_end: datetime
    request_count: int
    chat_count: int
    report_count: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


class UsageHistoryRead(APIModel):
    id: str
    usage_id: str
    occurred_at: datetime
    event_type: str
    operation: Optional[str]
    model_provider: Optional[str]
    model_name: Optional[str]
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    chat_id: Optional[str]
    report_id: Optional[str]


class RefreshTokenRead(APIModel):
    """Administrative/public-safe token view; token hashes are never exposed."""

    id: str
    user_id: str
    family_id: str
    expires_at: datetime
    revoked_at: Optional[datetime]
    last_used_at: Optional[datetime]
    revoked_reason: Optional[str]


class ProviderCredentialCreate(BaseModel):
    provider: Literal["groq", "deepseek", "openrouter"]
    api_key: SecretStr = Field(min_length=1)
    label: Optional[str] = Field(default=None, max_length=160)
    default_model_id: Optional[str] = Field(default=None, max_length=255)


class ProviderCredentialUpdate(BaseModel):
    label: Optional[str] = Field(default=None, max_length=160)
    default_model_id: Optional[str] = Field(default=None, max_length=255)
    status: Optional[Literal["active", "disabled"]] = None


class ProviderCredentialRead(APIModel):
    id: str
    provider: str
    label: Optional[str]
    key_fingerprint: str
    default_model_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class ProviderCredentialSelectionUpdate(BaseModel):
    """Persist the credential used for new Chat and Research requests."""

    credential_id: Optional[str] = None


class ProviderCredentialSelectionRead(BaseModel):
    credential_id: Optional[str] = None


class AvailableModelRead(BaseModel):
    id: str
    owned_by: Optional[str] = None
    supports_research: bool


class LLMCompletionCreate(BaseModel):
    """No API key is accepted here: only a stored credential reference."""

    message: str = Field(min_length=1)
    provider_credential_id: str
    model_id: Optional[str] = Field(default=None, max_length=255)
    chat_id: Optional[str] = None
    temperature: float = Field(default=0.3, ge=0, le=2)
    max_output_tokens: int = Field(default=1500, ge=1, le=65_536)
    structured_output: "StructuredOutputCreate | None" = None


class StructuredOutputCreate(BaseModel):
    """A strict JSON Schema contract for a single LLM completion."""

    name: str = Field(min_length=1, max_length=64)
    schema_: dict[str, Any] = Field(alias="schema")

    model_config = ConfigDict(populate_by_name=True)


class LLMCompletionRead(BaseModel):
    provider: str
    credential_id: str
    model_id: str
    content: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    structured_output: Any | None = None


class HealthRead(BaseModel):
    status: Literal["ok"]
    database: str
    version: str


class StorageHealthRead(BaseModel):
    status: Literal["ok"]
    backend: str


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)


class CLIDeviceLoginRequest(BaseModel):
    """Authenticate one installed CLI without an interactive account login."""

    device_token: SecretStr = Field(min_length=32, max_length=512)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: Literal["bearer"] = "bearer"


class WalkthroughRequest(BaseModel):
    """Body for claim/complete/dismiss. The user id is never accepted here; it is
    always derived from the authenticated caller."""

    version: int = Field(ge=1)


class WalkthroughClaimRead(BaseModel):
    show: bool
    walkthrough_key: str = Field(serialization_alias="walkthroughKey")
    version: int

    model_config = ConfigDict(populate_by_name=True)
