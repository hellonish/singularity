"""Retry behavior for the API worker's research model adapter.

The API research worker uses ``ProviderResearchModel`` (not the CLI's
``TerminalResearchModel``). A transient provider failure — most commonly a
Groq free-tier 429 during the parallel-planner fan-out — must be retried
rather than failing the whole run.
"""
from __future__ import annotations

import asyncio

import pytest

import api.research_runtime as research_runtime
from api.research_runtime import ProviderResearchModel, _retry_after_seconds
from engine.llm.groq import ProviderError
from engine.research_workflow.caps import RunCaps


def _model() -> ProviderResearchModel:
    return ProviderResearchModel(
        provider_name="groq",
        api_key="gsk_test",
        user_id="user-1",
        credential_id="cred-1",
        model_id="openai/gpt-oss-20b",
        caps=RunCaps.for_strength(2),
    )


def test_retryable_rate_limit_is_retried_after_backoff(monkeypatch) -> None:
    calls: list[int] = []
    slept: list[float] = []

    class FlakyProvider:
        async def complete(self, *, config, **kwargs):
            calls.append(config.max_output_tokens)
            if len(calls) == 1:
                raise ProviderError(
                    code="provider_rate_limited",
                    message="rate limited",
                    retryable=True,
                    retry_after_seconds="9.29s",
                )
            return type("Completion", (), {"content": '{"ok":true}'})()

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    model = _model()
    model._provider = FlakyProvider()
    monkeypatch.setattr(research_runtime.asyncio, "sleep", fake_sleep)

    content = asyncio.run(model.complete("Return JSON only", max_output_tokens=1_200))

    assert content == '{"ok":true}'
    assert len(calls) == 2  # one failure, one successful retry
    assert calls[1] > calls[0]  # retry raises the completion budget
    assert slept == [9.29]  # honors the advertised backoff before retrying


def test_non_retryable_failure_is_not_retried() -> None:
    calls: list[int] = []

    class DeadProvider:
        async def complete(self, **kwargs):
            calls.append(1)
            raise ProviderError(
                code="provider_credential_invalid",
                message="bad key",
                retryable=False,
            )

    model = _model()
    model._provider = DeadProvider()

    with pytest.raises(ProviderError):
        asyncio.run(model.complete("Return JSON only", max_output_tokens=500))
    assert calls == [1]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9.2925s", 9.2925),
        ("9.2925", 9.2925),
        ("120", 30.0),  # clamped to the ceiling
        (None, 0.0),
        ("", 0.0),
        ("junk", 0.0),
        ("-5", 0.0),
    ],
)
def test_retry_after_parsing(raw, expected) -> None:
    assert _retry_after_seconds(raw) == expected
