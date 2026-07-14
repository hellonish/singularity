"""Vector-store failures for report context, with a safe user-facing message.

Report context ingestion and retrieval both talk to the vector store, which can
be slow or unreachable under load. When that happens we must never let a
report-linked chat answer as if the report were present, and we must never leak
infrastructure detail to the client. This module carries the full server-side
cause (for logs) separately from the generic message shown to the user.
"""
from __future__ import annotations

from engine.research_workflow.runtime import ResearchInfrastructureError

# Shown verbatim to the end user. Deliberately generic: it reveals nothing about
# the vector store and frames the failure as transient and retryable.
LOAD_MESSAGE = "The system is currently experiencing a lot of load, please try again later."


class ReportContextError(ResearchInfrastructureError):
    """A classified report-context failure that hides infrastructure detail.

    The vector store backing report context is part of the research/chat
    backend, so a store outage is an infrastructure failure. Subclassing
    ``ResearchInfrastructureError`` lets the research worker classify an
    ingestion failure as transient (``reason: "infrastructure_unavailable"``)
    rather than a raw crash, matching the documented ``research.failed``
    contract.

    ``message`` is safe to return to a client. The originating exception is
    always logged at the raise site with full detail; it is chained here only
    so callers higher up can inspect it if needed, never so it is serialized.
    """

    def __init__(
        self,
        *,
        code: str = "report_context_unavailable",
        message: str = LOAD_MESSAGE,
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
