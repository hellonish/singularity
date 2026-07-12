from __future__ import annotations

import httpx
from openai import APIStatusError

from engine.llm.groq import GroqProviderError, _classify_groq_error


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
