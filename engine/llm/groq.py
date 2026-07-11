"""Stateless Groq provider using Groq's OpenAI-compatible API."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from engine.llm.config import LLMRequestConfig
from engine.llm.structured import StructuredOutputSpec

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
logger = logging.getLogger(__name__)


class GroqProviderError(RuntimeError):
    """A safe, classified provider failure that never exposes a secret."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool,
        retry_after_seconds: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class GroqModel:
    id: str
    owned_by: str | None = None


@dataclass(frozen=True)
class LLMCompletion:
    content: str
    input_tokens: int | None
    output_tokens: int | None
    structured_output: Any | None = None


class GroqProvider:
    """No client, key, or model is retained on this provider instance."""

    provider = "groq"

    async def list_models(self, *, api_key: str) -> list[GroqModel]:
        try:
            async with AsyncOpenAI(api_key=api_key, base_url=GROQ_BASE_URL) as client:
                page = await client.models.list()
        except Exception as exc:
            raise _classify_groq_error(exc, operation="retrieve models") from exc
        return sorted(
            (GroqModel(id=model.id, owned_by=getattr(model, "owned_by", None)) for model in page.data),
            key=lambda model: model.id,
        )

    async def complete(
        self,
        *,
        api_key: str,
        config: LLMRequestConfig,
        message: str,
        end_user_id: str,
        structured_output: StructuredOutputSpec | None = None,
    ) -> LLMCompletion:
        try:
            async with AsyncOpenAI(api_key=api_key, base_url=GROQ_BASE_URL) as client:
                request_data: dict[str, Any] = {
                    "model": config.model_id,
                    "messages": [{"role": "user", "content": message}],
                    "temperature": config.temperature,
                    "max_completion_tokens": config.max_output_tokens,
                    "user": end_user_id,
                }
                if structured_output is not None:
                    request_data["response_format"] = structured_output.groq_response_format()
                response = await client.chat.completions.create(**request_data)
        except Exception as exc:
            raise _classify_groq_error(exc, operation="complete request") from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise GroqProviderError("Groq returned no assistant content")
        try:
            parsed_output = structured_output.parse_and_validate(content) if structured_output else None
        except Exception as exc:
            raise GroqProviderError(
                code="provider_invalid_structured_output",
                message="Groq returned structured output that failed validation",
                retryable=True,
            ) from exc
        usage = response.usage
        return LLMCompletion(
            content=content,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            structured_output=parsed_output,
        )


def _classify_groq_error(exc: Exception, *, operation: str) -> GroqProviderError:
    """Convert SDK/network failures into stable API-safe outcomes.

    Raw provider bodies are inspected only to distinguish exhausted credits from
    throttling; they are never sent to the caller because they may contain
    account-specific details.
    """

    logger.warning("Groq %s failed: %s", operation, type(exc).__name__)
    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return GroqProviderError(
            code="provider_unavailable",
            message=f"Groq is temporarily unavailable while attempting to {operation}",
            retryable=True,
        )
    if isinstance(exc, APIStatusError):
        status_code = exc.status_code
        headers = exc.response.headers if exc.response is not None else {}
        retry_after = headers.get("retry-after")
        if status_code == 401:
            return GroqProviderError(
                code="provider_credential_invalid",
                message="The saved Groq credential is invalid or expired",
                retryable=False,
            )
        if status_code == 403:
            return GroqProviderError(
                code="provider_permission_denied",
                message="The saved Groq credential does not have permission for this request",
                retryable=False,
            )
        if status_code in {402, 429}:
            body_text = str(getattr(exc, "body", "")).lower()
            if status_code == 402 or any(term in body_text for term in ("credit", "quota", "spend limit", "balance")):
                return GroqProviderError(
                    code="provider_credits_exhausted",
                    message="The Groq account has reached its credit or spend limit",
                    retryable=False,
                )
            return GroqProviderError(
                code="provider_rate_limited",
                message="Groq rate limit reached; retry after the indicated delay",
                retryable=True,
                retry_after_seconds=retry_after,
            )
        if status_code == 498:
            return GroqProviderError(
                code="provider_capacity_unavailable",
                message="Groq flex capacity is temporarily unavailable",
                retryable=True,
                retry_after_seconds=retry_after,
            )
        if status_code in {400, 404, 413, 422, 424}:
            body_text = str(getattr(exc, "body", "")).lower()
            if "json_validate_failed" in body_text:
                return GroqProviderError(
                    code="provider_structured_output_unsatisfied",
                    message="Groq could not satisfy the structured-output schema; simplify the schema or increase the output-token limit",
                    retryable=False,
                )
            return GroqProviderError(
                code="provider_request_rejected",
                message="Groq rejected this request; check the selected model and request settings",
                retryable=False,
            )
        if status_code >= 500:
            return GroqProviderError(
                code="provider_unavailable",
                message="Groq is temporarily unavailable; retry later",
                retryable=True,
                retry_after_seconds=retry_after,
            )
    return GroqProviderError(
        code="provider_error",
        message=f"Unable to {operation} with Groq",
        retryable=False,
    )
