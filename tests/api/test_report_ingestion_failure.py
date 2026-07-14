"""Report ingestion failure must fail the run, not silently mark it ready."""
from __future__ import annotations

import logging

import pytest

from api.research_runtime import _ingest_report_or_fail
from api.services.report_context_errors import LOAD_MESSAGE, ReportContextError


class _ExplodingVectorStore:
    def ingest_text(self, **kwargs):
        raise ConnectionError("qdrant unreachable at http://localhost:6333")


class _RecordingVectorStore:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def ingest_text(self, **kwargs):
        self.calls.append(kwargs)
        return []


def test_ingestion_failure_raises_generic_error_and_logs_full_cause(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ReportContextError) as exc:
            _ingest_report_or_fail(
                _ExplodingVectorStore(),
                user_id="user_a",
                report_id="report_a",
                run_id="run_a",
                version_number=1,
                content="Finalized report body.",
                title="Report",
            )

    # User-facing message is the generic load message; the raised error chains
    # the real cause for callers but never serializes infrastructure detail.
    assert exc.value.message == LOAD_MESSAGE
    assert exc.value.code == "report_context_unavailable"
    assert isinstance(exc.value.__cause__, ConnectionError)

    # Operators get the full cause in the log.
    assert any("report context ingestion failed" in r.message for r in caplog.records)
    assert any("qdrant unreachable" in r.getMessage() for r in caplog.records)


def test_successful_ingestion_does_not_raise() -> None:
    store = _RecordingVectorStore()
    _ingest_report_or_fail(
        store,
        user_id="user_a",
        report_id="report_a",
        run_id="run_a",
        version_number=2,
        content="Finalized report body.",
        title="Report",
    )
    assert len(store.calls) == 1
    assert store.calls[0]["scope"].report_id == "report_a"
