from __future__ import annotations

import httpx
from openai import APIStatusError

from engine.llm.groq import GroqProviderError, _classify_groq_error
from engine.llm.openrouter import OpenRouterProvider
from engine.llm.config import LLMRequestConfig


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
