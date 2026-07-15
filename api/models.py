"""Database schema for API v2.

IDs are UUID strings rather than database-native UUID columns. This keeps the
first SQLite deployment simple while preserving stable identifiers when moving
to PostgreSQL. JSON fields hold optional extension data; core queryable facts
remain normalized columns with indexes and constraints.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _new_id() -> str:
    return str(uuid.uuid4())


_NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


class IdMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[Optional[str]] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    auth_provider: Mapped[Optional[str]] = mapped_column(String(48))
    external_subject: Mapped[Optional[str]] = mapped_column(String(255))
    profile_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    chats: Mapped[list["Chat"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    research_runs: Mapped[list["ResearchRun"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    research_preparations: Mapped[list["ResearchPreparation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    llm_credentials: Mapped[list["LLMProviderCredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    usage: Mapped["UsageAccount"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("status IN ('active', 'suspended', 'deleted')", name="user_status"),
        UniqueConstraint("auth_provider", "external_subject", name="user_auth_subject"),
    )


class LLMProviderCredential(IdMixin, TimestampMixin, Base):
    """A user's encrypted, provider-specific BYOK credential.

    The plaintext API key never leaves request memory and is never exposed by
    API schemas. A default model is scoped to this credential because a user
    may connect more than one account for the same provider.
    """

    __tablename__ = "llm_provider_credentials"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(48), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(160))
    encrypted_secret: Mapped[str] = mapped_column(Text, nullable=False)
    key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    default_model_id: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    credential_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[User] = relationship(back_populates="llm_credentials")
    chats: Mapped[list["Chat"]] = relationship(back_populates="provider_credential")

    __table_args__ = (
        CheckConstraint("provider IN ('groq', 'deepseek', 'openrouter')", name="llm_credential_provider"),
        CheckConstraint("status IN ('active', 'disabled')", name="llm_credential_status"),
        Index("ix_llm_credentials_user_provider", "user_id", "provider"),
    )


class Chat(IdMixin, TimestampMixin, Base):
    __tablename__ = "chats"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="SET NULL"), index=True
    )
    provider_credential_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("llm_provider_credentials.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    model_provider: Mapped[Optional[str]] = mapped_column(String(48))
    model_name: Mapped[Optional[str]] = mapped_column(String(128))
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    chat_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[User] = relationship(back_populates="chats")
    report: Mapped[Optional["Report"]] = relationship(back_populates="chats")
    provider_credential: Mapped[Optional[LLMProviderCredential]] = relationship(back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan", order_by="Message.sequence"
    )
    summaries: Mapped[list["ChatSummary"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan", order_by="ChatSummary.sequence"
    )

    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived', 'deleted')", name="chat_status"),
        Index("ix_chats_user_last_message", "user_id", "last_message_at"),
    )


class ChatSummary(IdMixin, TimestampMixin, Base):
    __tablename__ = "chat_summaries"

    chat_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    through_message_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="SET NULL"), index=True
    )
    token_count: Mapped[Optional[int]] = mapped_column(Integer)
    summary_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    chat: Mapped[Chat] = relationship(back_populates="summaries")

    __table_args__ = (
        CheckConstraint("sequence >= 1", name="chat_summary_sequence"),
        UniqueConstraint("chat_id", "sequence", name="chat_summary_sequence"),
    )


class Message(IdMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    chat_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[Optional[str]] = mapped_column(String(48))
    model_name: Mapped[Optional[str]] = mapped_column(String(128))
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    parent_message_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="SET NULL"), index=True
    )
    message_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    chat: Mapped[Chat] = relationship(back_populates="messages")

    __table_args__ = (
        CheckConstraint("sequence >= 1", name="message_sequence"),
        CheckConstraint("role IN ('system', 'user', 'assistant', 'tool')", name="message_role"),
        UniqueConstraint("chat_id", "sequence", name="message_sequence"),
        Index("ix_messages_chat_created", "chat_id", "created_at"),
    )


class UsageAccount(IdMixin, TimestampMixin, Base):
    """One durable usage identity per user; detailed events and rollups hang from it."""

    __tablename__ = "usage_accounts"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    lifetime_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, default=Decimal("0"))

    user: Mapped[User] = relationship(back_populates="usage")
    rollups: Mapped[list["UsageRollup"]] = relationship(
        back_populates="usage", cascade="all, delete-orphan"
    )
    history: Mapped[list["UsageHistory"]] = relationship(
        back_populates="usage", cascade="all, delete-orphan"
    )


class UsageRollup(IdMixin, TimestampMixin, Base):
    """Queryable daily, weekly, and monthly usage mapping for a UsageAccount."""

    __tablename__ = "usage_rollups"

    usage_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("usage_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_kind: Mapped[str] = mapped_column(String(12), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chat_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, default=Decimal("0"))
    rollup_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    usage: Mapped[UsageAccount] = relationship(back_populates="rollups")

    __table_args__ = (
        CheckConstraint("period_kind IN ('day', 'week', 'month')", name="usage_period_kind"),
        CheckConstraint("period_end > period_start", name="usage_period_bounds"),
        UniqueConstraint("usage_id", "period_kind", "period_start", name="usage_period"),
        Index("ix_usage_rollups_lookup", "usage_id", "period_kind", "period_start"),
    )


class UsageHistory(IdMixin, TimestampMixin, Base):
    __tablename__ = "usage_history"

    usage_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("usage_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[Optional[str]] = mapped_column(String(128))
    model_provider: Mapped[Optional[str]] = mapped_column(String(48))
    model_name: Mapped[Optional[str]] = mapped_column(String(128))
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, default=Decimal("0"))
    chat_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("chats.id", ondelete="SET NULL"), index=True
    )
    report_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="SET NULL"), index=True
    )
    event_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    usage: Mapped[UsageAccount] = relationship(back_populates="history")

    __table_args__ = (Index("ix_usage_history_usage_time", "usage_id", "occurred_at"),)


class Report(IdMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    source: Mapped[Optional[str]] = mapped_column(String(64))
    report_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[User] = relationship(back_populates="reports")
    versions: Mapped[list["ReportVersion"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="ReportVersion.version_number"
    )
    chats: Mapped[list[Chat]] = relationship(back_populates="report")
    research_runs: Mapped[list["ResearchRun"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'processing', 'ready', 'archived', 'failed')", name="report_status"),
        Index("ix_reports_user_created", "user_id", "created_at"),
    )


class ReportVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "report_versions"

    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("report_versions.id", ondelete="SET NULL"), index=True
    )
    content: Mapped[Optional[str]] = mapped_column(Text)
    content_uri: Mapped[Optional[str]] = mapped_column(String(1024), unique=True)
    content_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_format: Mapped[str] = mapped_column(String(32), nullable=False, default="markdown")
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    change_note: Mapped[Optional[str]] = mapped_column(Text)
    version_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    report: Mapped[Report] = relationship(back_populates="versions")

    __table_args__ = (
        CheckConstraint("version_number >= 1", name="report_version_number"),
        UniqueConstraint("report_id", "version_number", name="report_version_number"),
        Index("ix_report_versions_report_number", "report_id", "version_number"),
    )


class ResearchRun(IdMixin, TimestampMixin, Base):
    """A durable request for future engine execution.

    Keeping the run separate from Report lets one report retain its version
    history while multiple research attempts are recorded independently.
    """

    __tablename__ = "research_runs"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="SET NULL"), index=True
    )
    preparation_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("research_preparations.id", ondelete="SET NULL"), unique=True, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    engine_version: Mapped[Optional[str]] = mapped_column(String(128))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    run_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[User] = relationship(back_populates="research_runs")
    report: Mapped[Optional[Report]] = relationship(back_populates="research_runs")
    preparation: Mapped[Optional["ResearchPreparation"]] = relationship(back_populates="run")
    events: Mapped[list["ResearchRunEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="ResearchRunEvent.sequence"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="research_run_status",
        ),
        Index("ix_research_runs_user_created", "user_id", "created_at"),
    )


class ResearchPreparation(IdMixin, TimestampMixin, Base):
    """Durable intake state that exists before a paid research run starts."""

    __tablename__ = "research_preparations"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_credential_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("llm_provider_credentials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    approval_mode: Mapped[str] = mapped_column(String(12), nullable=False, default="ask")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    model_id: Mapped[Optional[str]] = mapped_column(String(255))
    strength: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    current_question_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    plan_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    answers: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    final_brief: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="research_preparations")
    run: Mapped[Optional[ResearchRun]] = relationship(back_populates="preparation", uselist=False)

    __table_args__ = (
        CheckConstraint("approval_mode IN ('ask', 'auto')", name="research_preparation_mode"),
        CheckConstraint(
            "status IN ('draft', 'awaiting_input', 'ready', 'started', 'cancelled', 'failed')",
            name="research_preparation_status",
        ),
        CheckConstraint("strength >= 1 AND strength <= 3", name="research_preparation_strength"),
        Index("ix_research_preparations_user_created", "user_id", "created_at"),
    )


class ResearchRunEvent(IdMixin, Base):
    """Durable progress event used to replay a run after an SSE reconnect."""

    __tablename__ = "research_run_events"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(96), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run: Mapped[ResearchRun] = relationship(back_populates="events")

    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="research_run_event_sequence"),
        Index("ix_research_run_events_run_sequence", "run_id", "sequence"),
    )


class UserWalkthrough(Base):
    """One row per user per walkthrough version, granting at-most-once display.

    The walkthrough UI/configuration lives in frontend code because selectors,
    routes, and component IDs are tied to the deployed frontend. Only user
    progress is persisted here. The composite primary key is what makes the
    ``claim`` operation atomic: an ``INSERT ... ON CONFLICT DO NOTHING`` either
    inserts the sole row (this caller wins the claim) or conflicts (someone —
    another tab, device, or duplicated request — already claimed it).

    Bumping ``version`` for a substantially changed walkthrough lets existing
    users see the new one once without deleting old records.
    """

    __tablename__ = "user_walkthroughs"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    walkthrough_key: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="claimed")
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "walkthrough_key", "version", name="user_walkthrough"),
        CheckConstraint(
            "status IN ('claimed', 'completed', 'dismissed')", name="user_walkthrough_status"
        ),
        Index("ix_user_walkthroughs_user_status", "user_id", "status"),
    )


class RefreshToken(IdMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    family_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(128))
    token_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    __table_args__ = (Index("ix_refresh_tokens_user_family", "user_id", "family_id"),)
