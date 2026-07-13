"""Stateless Groq provider using Groq's OpenAI-compatible API."""
from __future__ import annotations

import logging
import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from engine.llm.config import LLMRequestConfig
from engine.llm.structured import StructuredOutputSpec
from engine.chat.prompt import build_runtime_system_prompt

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
logger = logging.getLogger(__name__)


class ProviderError(RuntimeError):
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


# Backwards-compatible import name. OpenRouter and DeepSeek share this error
# contract, so the runtime class name must not falsely identify every failure
# as Groq.
GroqProviderError = ProviderError


@dataclass(frozen=True)
class GroqModel:
    id: str
    owned_by: str | None = None
    context_window: int | None = None
    max_completion_tokens: int | None = None
    active: bool = True


@dataclass(frozen=True)
class LLMCompletion:
    content: str
    input_tokens: int | None
    output_tokens: int | None
    structured_output: Any | None = None


@dataclass(frozen=True)
class LLMToolCall:
    name: str
    arguments: dict[str, Any]


class GroqProvider:
    """No client, key, or model is retained on this provider instance."""

    provider = "groq"
    base_url = GROQ_BASE_URL
    display_name = "Groq"
    max_output_parameter = "max_completion_tokens"

    def _classify_error(self, exc: Exception, *, operation: str) -> GroqProviderError:
        return _classify_groq_error(exc, operation=operation, provider_name=self.display_name)

    def _apply_reasoning(self, request_data: dict[str, Any], effort: str | None) -> None:
        if effort is None:
            return
        if self.provider == "openrouter":
            extra_body = dict(request_data.get("extra_body", {}))
            extra_body["reasoning"] = {"effort": effort, "exclude": True}
            request_data["extra_body"] = extra_body
        else:
            request_data["reasoning_effort"] = effort

    async def list_models(self, *, api_key: str) -> list[GroqModel]:
        try:
            async with AsyncOpenAI(api_key=api_key, base_url=self.base_url) as client:
                page = await client.models.list()
        except Exception as exc:
            raise self._classify_error(exc, operation="retrieve models") from exc
        return sorted(
            (GroqModel(id=model.id, owned_by=getattr(model, "owned_by", None)) for model in page.data),
            key=lambda model: model.id,
        )

    async def retrieve_model(self, *, api_key: str, model_id: str) -> GroqModel:
        """Read the selected model's live context and completion limits."""

        try:
            async with AsyncOpenAI(api_key=api_key, base_url=self.base_url) as client:
                model = await client.models.retrieve(model_id)
        except Exception as exc:
            raise self._classify_error(exc, operation="retrieve model limits") from exc
        return GroqModel(
            id=model.id,
            owned_by=getattr(model, "owned_by", None),
            context_window=getattr(model, "context_window", None),
            max_completion_tokens=getattr(model, "max_completion_tokens", None),
            active=bool(getattr(model, "active", True)),
        )

    async def stream_chat(
        self,
        *,
        api_key: str,
        config: LLMRequestConfig,
        messages: Sequence[dict[str, str]],
        end_user_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield real Groq text deltas while retaining no client or key state."""

        try:
            async with AsyncOpenAI(api_key=api_key, base_url=self.base_url) as client:
                request_data: dict[str, Any] = {
                    "model": config.model_id,
                    "messages": list(messages),
                    "temperature": config.temperature,
                    self.max_output_parameter: config.max_output_tokens,
                    "stream": True,
                }
                if end_user_id is not None:
                    request_data["user"] = end_user_id
                self._apply_reasoning(request_data, config.reasoning_effort)
                stream = await client.chat.completions.create(**request_data)
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
        except Exception as exc:
            raise self._classify_error(exc, operation="stream chat response") from exc

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
            async with AsyncOpenAI(api_key=api_key, base_url=self.base_url) as client:
                request_data: dict[str, Any] = {
                    "model": config.model_id,
                    "messages": [
                        {"role": "system", "content": build_runtime_system_prompt()},
                        {"role": "user", "content": message},
                    ],
                    "temperature": config.temperature,
                    self.max_output_parameter: config.max_output_tokens,
                    "user": end_user_id,
                }
                if structured_output is not None:
                    request_data["response_format"] = structured_output.groq_response_format()
                    if self.provider == "openrouter":
                        # Do not let OpenRouter silently route a JSON-mode
                        # request to a backend that lacks response_format.
                        request_data["extra_body"] = {
                            "provider": {"require_parameters": True}
                        }
                self._apply_reasoning(request_data, config.reasoning_effort)
                response = await client.chat.completions.create(**request_data)
        except Exception as exc:
            raise self._classify_error(exc, operation="complete request") from exc

        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice else None
        if not content:
            finish_reason = getattr(choice, "finish_reason", None) or "unknown"
            raise GroqProviderError(
                code="provider_empty_response",
                message=(
                    f"{self.display_name} model {config.model_id} returned no assistant content "
                    f"(finish_reason={finish_reason}, output_limit={config.max_output_tokens})"
                ),
                retryable=True,
            )
        try:
            parsed_output = structured_output.parse_and_validate(content) if structured_output else None
        except Exception as exc:
            finish_reason = getattr(choice, "finish_reason", None) or "unknown"
            detail = f"finish_reason={finish_reason}, output_limit={config.max_output_tokens}"
            if finish_reason == "length":
                detail += "; the completion was truncated, so a larger output-token budget is required"
            raise GroqProviderError(
                code="provider_invalid_structured_output",
                message=f"{self.display_name} returned structured output that failed validation ({detail})",
                retryable=True,
            ) from exc
        usage = response.usage
        return LLMCompletion(
            content=content,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            structured_output=parsed_output,
        )

    async def plan_tool_call(
        self,
        *,
        api_key: str,
        config: LLMRequestConfig,
        messages: Sequence[dict[str, str]],
        tools: list[dict[str, Any]],
        end_user_id: str | None = None,
    ) -> LLMToolCall | None:
        """Ask Groq for at most one validated tool decision, without streaming."""
        try:
            async with AsyncOpenAI(api_key=api_key, base_url=self.base_url) as client:
                request_data: dict[str, Any] = {
                    "model": config.model_id,
                    "messages": list(messages),
                    "temperature": config.temperature,
                    self.max_output_parameter: min(config.max_output_tokens, 512),
                    "tools": tools,
                    "tool_choice": "auto",
                }
                if end_user_id is not None:
                    request_data["user"] = end_user_id
                self._apply_reasoning(request_data, config.reasoning_effort)
                response = await client.chat.completions.create(**request_data)
        except Exception as exc:
            classified = self._classify_error(exc, operation="plan chat tool use")
            # GPT-OSS can occasionally emit an invalid local-tool argument
            # object. Groq returns that as HTTP 400 before giving us a model
            # response. Planning is optional, so fall back to normal chat
            # rather than failing the whole turn.
            if classified.code == "provider_invalid_tool_generation":
                return None
            raise classified from exc
        message = response.choices[0].message if response.choices else None
        calls = getattr(message, "tool_calls", None) if message else None
        if not calls:
            return None
        call = calls[0]
        try:
            arguments = json.loads(call.function.arguments or "{}")
        except (TypeError, json.JSONDecodeError) as exc:
            raise GroqProviderError(
                code="provider_invalid_tool_arguments",
                message="Groq returned malformed chat tool arguments",
                retryable=True,
            ) from exc
        if not isinstance(arguments, dict):
            raise GroqProviderError(
                code="provider_invalid_tool_arguments",
                message="Groq returned non-object chat tool arguments",
                retryable=True,
            )
        return LLMToolCall(name=call.function.name, arguments=arguments)


def _classify_groq_error(exc: Exception, *, operation: str, provider_name: str = "Groq") -> GroqProviderError:
    """Convert SDK/network failures into stable API-safe outcomes.

    Raw provider bodies are inspected only to distinguish exhausted credits from
    throttling; they are never sent to the caller because they may contain
    account-specific details.
    """

    logger.warning("%s %s failed: %s", provider_name, operation, type(exc).__name__)
    if isinstance(exc, json.JSONDecodeError):
        return GroqProviderError(
            code="provider_invalid_json_response",
            message=f"{provider_name} returned an invalid JSON HTTP response while attempting to {operation}",
            retryable=True,
        )
    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return GroqProviderError(
            code="provider_unavailable",
            message=f"{provider_name} is temporarily unavailable while attempting to {operation}",
            retryable=True,
        )
    if isinstance(exc, APIStatusError):
        status_code = exc.status_code
        headers = exc.response.headers if exc.response is not None else {}
        retry_after = headers.get("retry-after")
        body = getattr(exc, "body", None)
        if status_code == 400 and isinstance(body, dict) and body.get("failed_generation"):
            return GroqProviderError(
                code="provider_invalid_tool_generation",
                message="Groq rejected an invalid model-generated tool call",
                retryable=True,
            )
        if status_code == 401:
            return GroqProviderError(
                code="provider_credential_invalid",
                message=f"The saved {provider_name} credential is invalid or expired",
                retryable=False,
            )
        if status_code == 403:
            return GroqProviderError(
                code="provider_permission_denied",
                message=f"The saved {provider_name} credential does not have permission for this request",
                retryable=False,
            )
        if status_code in {402, 429}:
            body_text = str(getattr(exc, "body", "")).lower()
            if status_code == 402 or any(term in body_text for term in ("credit", "quota", "spend limit", "balance")):
                return GroqProviderError(
                    code="provider_credits_exhausted",
                message=f"The {provider_name} account has reached its credit or spend limit",
                    retryable=False,
                )
            return GroqProviderError(
                code="provider_rate_limited",
                message=f"{provider_name} rate limit reached; retry after the indicated delay",
                retryable=True,
                retry_after_seconds=retry_after,
            )
        if status_code == 498:
            return GroqProviderError(
                code="provider_capacity_unavailable",
                message=f"{provider_name} capacity is temporarily unavailable",
                retryable=True,
                retry_after_seconds=retry_after,
            )
        if status_code in {400, 404, 413, 422, 424}:
            body_text = str(getattr(exc, "body", "")).lower()
            if "json_validate_failed" in body_text:
                return GroqProviderError(
                    code="provider_structured_output_unsatisfied",
                    message=f"{provider_name} could not satisfy the structured-output schema; simplify the schema or increase the output-token limit",
                    retryable=False,
                )
            return GroqProviderError(
                code="provider_request_rejected",
                message=f"{provider_name} rejected this request; check the selected model and request settings",
                retryable=False,
            )
        if status_code >= 500:
            return GroqProviderError(
                code="provider_unavailable",
                message=f"{provider_name} is temporarily unavailable; retry later",
                retryable=True,
                retry_after_seconds=retry_after,
            )
    return GroqProviderError(
        code="provider_error",
        message=f"Unable to {operation} with {provider_name}",
        retryable=False,
    )
