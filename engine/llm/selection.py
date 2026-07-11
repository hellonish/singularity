from __future__ import annotations

from engine.llm.config import LLMRequestConfig


def resolve_request_config(
    *,
    provider: str,
    credential_id: str,
    request_model_id: str | None,
    conversation_model_id: str | None,
    credential_default_model_id: str | None,
    application_fallback_model_id: str,
    temperature: float = 0.3,
    max_output_tokens: int = 1500,
) -> LLMRequestConfig:
    """Resolve model selection without retaining mutable provider state.

    Precedence: explicit request, conversation choice, credential default,
    then application fallback.
    """

    model_id = (
        request_model_id
        or conversation_model_id
        or credential_default_model_id
        or application_fallback_model_id
    )
    return LLMRequestConfig(
        provider=provider,
        credential_id=credential_id,
        model_id=model_id,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
