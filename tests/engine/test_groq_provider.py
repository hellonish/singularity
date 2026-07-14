from __future__ import annotations

import asyncio

import httpx
from openai import APIStatusError

from engine.llm.groq import GroqProvider, GroqProviderError, _classify_groq_error
from engine.llm.openrouter import OpenRouterProvider
from engine.llm.config import LLMRequestConfig


def _raw_response_client(monkeypatch, *, headers=None, raise_exc=None):
    """Install a fake AsyncOpenAI whose with_raw_response.create returns headers."""

    class RawResponse:
        def __init__(self):
            self.headers = headers or {}

    class WithRaw:
        async def create(self, **kwargs):
            if raise_exc is not None:
                raise raise_exc
            return RawResponse()

    class Completions:
        with_raw_response = WithRaw()

    class Client:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {"completions": Completions()})()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr("engine.llm.groq.AsyncOpenAI", Client)


def test_probe_tier_flags_free_from_low_daily_limit(monkeypatch) -> None:
    _raw_response_client(monkeypatch, headers={"x-ratelimit-limit-requests": "1000"})
    tier = asyncio.run(GroqProvider().probe_tier(api_key="k", model_id="m"))
    assert tier == "free"


def test_probe_tier_flags_paid_from_high_daily_limit(monkeypatch) -> None:
    _raw_response_client(monkeypatch, headers={"x-ratelimit-limit-requests": "500000"})
    tier = asyncio.run(GroqProvider().probe_tier(api_key="k", model_id="m"))
    assert tier == "paid"


def test_probe_tier_unknown_when_header_missing(monkeypatch) -> None:
    _raw_response_client(monkeypatch, headers={})
    tier = asyncio.run(GroqProvider().probe_tier(api_key="k", model_id="m"))
    assert tier == "unknown"


def test_probe_tier_unknown_on_probe_error(monkeypatch) -> None:
    _raw_response_client(monkeypatch, raise_exc=RuntimeError("boom"))
    tier = asyncio.run(GroqProvider().probe_tier(api_key="k", model_id="m"))
    assert tier == "unknown"


def test_probe_tier_unknown_for_non_groq_provider() -> None:
    # OpenRouter reuses GroqProvider but has no free-tier research gate.
    tier = asyncio.run(OpenRouterProvider().probe_tier(api_key="k", model_id="m"))
    assert tier == "unknown"


def test_invalid_tool_generation_has_a_safe_classification() -> None:
    response = httpx.Response(
        400,
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )
    error = APIStatusError(
        "Invalid tool call generated",
        response=response,
        body={"failed_generation": {"reason": "Tool call arguments are not valid JSON"}},
    )
    classified = _classify_groq_error(error, operation="plan chat tool use")

    assert isinstance(classified, GroqProviderError)
    assert classified.code == "provider_invalid_tool_generation"
    assert classified.retryable is True


def test_openrouter_empty_completion_names_the_actual_provider(monkeypatch) -> None:
    class Message:
        content = None

    class Choice:
        message = Message()
        finish_reason = "length"

    class Response:
        choices = [Choice()]
        usage = None

    class Completions:
        async def create(self, **kwargs):
            return Response()

    class Client:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {"completions": Completions()})()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr("engine.llm.groq.AsyncOpenAI", Client)
    config = LLMRequestConfig(
        provider="openrouter",
        credential_id="test",
        model_id="deepseek/deepseek-r1",
        max_output_tokens=500,
    )

    import asyncio
    try:
        asyncio.run(OpenRouterProvider().complete(
            api_key="test", config=config, message="JSON", end_user_id="test"
        ))
    except GroqProviderError as exc:
        assert exc.code == "provider_empty_response"
        assert str(exc) == (
            "OpenRouter model deepseek/deepseek-r1 returned no assistant content "
            "(finish_reason=length, output_limit=500)"
        )
    else:
        raise AssertionError("expected provider_empty_response")
