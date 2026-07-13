"""Tenant-scoped vector-store models.

Ownership is part of every payload because embeddings carry no access-control
information.  A scope is required for every ingest and every search.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalScope:
    """Server-authorized scope for an isolated vector operation."""

    user_id: str
    workspace_id: str | None = None
    conversation_id: str | None = None
    project_id: str | None = None
    report_id: str | None = None
    document_id: str | None = None
    research_run_id: str | None = None
    visibility: str = "private"

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise ValueError("user_id is required for vector-store isolation")
        if self.visibility not in {"private", "workspace", "public"}:
            raise ValueError("visibility must be private, workspace, or public")

    def payload_filter(self) -> dict[str, str]:
        """Return mandatory ownership filters plus explicitly requested scope."""
        fields = {
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "conversation_id": self.conversation_id,
            "project_id": self.project_id,
            "report_id": self.report_id,
            "document_id": self.document_id,
            "research_run_id": self.research_run_id,
        }
        return {key: value for key, value in fields.items() if value is not None}


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    embedding: list[float]
    scope: RetrievalScope
    source_type: str
    document_id: str
    source_url: str = ""
    source_title: str = ""
    credibility: float = 0.5
    metadata: dict = field(default_factory=dict)
    chunk_index: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("chunk text must not be empty")
        if not self.document_id.strip():
            raise ValueError("document_id must not be empty")
        if not 0.0 <= self.credibility <= 1.0:
            raise ValueError("credibility must be between 0 and 1")

    def payload(self) -> dict[str, object]:
        return {
            **self.scope.payload_filter(),
            "visibility": self.scope.visibility,
            "source_type": self.source_type,
            "document_id": self.document_id,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "credibility": self.credibility,
            "metadata": self.metadata,
            "chunk_index": self.chunk_index,
            "text": self.text,
        }

    @classmethod
    def from_qdrant_point(cls, point) -> "DocumentChunk":
        payload = point.payload or {}
        scope = RetrievalScope(
            user_id=str(payload["user_id"]),
            workspace_id=_optional(payload, "workspace_id"),
            conversation_id=_optional(payload, "conversation_id"),
            project_id=_optional(payload, "project_id"),
            report_id=_optional(payload, "report_id"),
            document_id=_optional(payload, "document_id"),
            research_run_id=_optional(payload, "research_run_id"),
            visibility=str(payload.get("visibility", "private")),
        )
        return cls(
            id=str(point.id),
            text=str(payload.get("text", "")),
            embedding=[],
            scope=scope,
            source_type=str(payload.get("source_type", "unknown")),
            document_id=str(payload.get("document_id", "")),
            source_url=str(payload.get("source_url", "")),
            source_title=str(payload.get("source_title", "")),
            credibility=float(payload.get("credibility", 0.5)),
            metadata=dict(payload.get("metadata", {})),
            chunk_index=int(payload.get("chunk_index", 0)),
        )


def _optional(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    return str(value) if value is not None else None
