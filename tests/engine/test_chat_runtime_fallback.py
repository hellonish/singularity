"""Fallback and Modal-error-classification behavior for the chat runtime."""
from __future__ import annotations

import asyncio

from engine.chat.modal_tools import ChatToolResult
from engine.chat.retry import is_retryable_exception
from engine.chat.runtime import _web_fetch_fallback


class _RecordingExecutor:
    def __init__(self, result: ChatToolResult | None = None, raises: Exception | None = None) -> None:
        self._result = result
        self._raises = raises
        self.invocations: list = []

    async def execute(self, invocation):
        self.invocations.append(invocation)
        if self._raises is not None:
            raise self._raises
        return self._result


def _ok_result() -> ChatToolResult:
    return ChatToolResult(
        content="page body",
        sources=[{"title": "Repo", "url": "https://github.com/hellonish/singularity"}],
        credibility_base=0.75,
        error=None,
    )


def test_fallback_fetches_url_from_query_and_returns_executed_call() -> None:
    executor = _RecordingExecutor(result=_ok_result())
    fetched = asyncio.run(
        _web_fetch_fallback(
            executor,
            "What do you think about https://github.com/hellonish/singularity.git ?",
            "run_1",
            120,
        )
    )
    assert fetched is not None
    assert fetched.tool_name == "web_fetch"
    invocation = executor.invocations[0]
    assert invocation.tool_name == "web_fetch"
    assert invocation.arguments["url"] == "https://github.com/hellonish/singularity.git"
    # A tool call can run for at most 60s on the fallback path.
    assert invocation.timeout_seconds == 60


def test_fallback_returns_none_when_query_has_no_url() -> None:
    executor = _RecordingExecutor(result=_ok_result())
    assert asyncio.run(_web_fetch_fallback(executor, "no link here", "run_1", 120)) is None
    assert executor.invocations == []


def test_fallback_swallows_executor_failure() -> None:
    executor = _RecordingExecutor(raises=RuntimeError("sandbox down"))
    result = asyncio.run(
        _web_fetch_fallback(executor, "see https://example.com/x", "run_1", 120)
    )
    assert result is None


def test_fallback_rejects_errored_or_empty_result() -> None:
    errored = ChatToolResult("", [], 0.0, "blocked")
    executor = _RecordingExecutor(result=errored)
    assert asyncio.run(_web_fetch_fallback(executor, "see https://example.com", "r", 120)) is None


def test_modal_invalid_error_is_permanent() -> None:
    import modal.exception as modal_exc

    assert is_retryable_exception(modal_exc.InvalidError("bad arg")) is False
    assert is_retryable_exception(modal_exc.NotFoundError("missing")) is False


def test_modal_resource_exhausted_is_retryable() -> None:
    import modal.exception as modal_exc

    assert is_retryable_exception(modal_exc.ResourceExhaustedError("busy")) is True
