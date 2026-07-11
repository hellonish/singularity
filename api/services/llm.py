"""Request-scoped orchestration between persisted BYOK credentials and providers."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.credential_crypto import decrypt_secret
from api.config import settings
from api.models import Chat, User
from api.schemas import LLMCompletionCreate
from api.services.llm_credentials import get_credential
from engine.llm import GroqProvider, resolve_request_config
from engine.llm.groq import GroqProviderError, GroqModel, LLMCompletion
from engine.llm.structured import STRICT_STRUCTURED_OUTPUT_MODELS, StructuredOutputError, StructuredOutputSpec


def _groq_error(exc: GroqProviderError) -> HTTPException:
    headers = {"Retry-After": exc.retry_after_seconds} if exc.retry_after_seconds else None
    http_status = (
        status.HTTP_429_TOO_MANY_REQUESTS
        if exc.code == "provider_rate_limited"
        else status.HTTP_503_SERVICE_UNAVAILABLE
        if exc.retryable
        else status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable},
        headers=headers,
    )


async def list_models(
    session: AsyncSession,
    user: User,
    credential_id: str,
) -> list[GroqModel]:
    credential = await get_credential(session, user.id, credential_id)
    if credential.provider != "groq":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported provider")
    api_key = decrypt_secret(credential.encrypted_secret)
    try:
        return await GroqProvider().list_models(api_key=api_key)
    except GroqProviderError as exc:
        raise _groq_error(exc) from exc


async def complete(
    session: AsyncSession,
    user: User,
    body: LLMCompletionCreate,
) -> tuple[LLMCompletion, object]:
    credential = await get_credential(session, user.id, body.provider_credential_id)
    if credential.provider != "groq":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported provider")

    conversation_model_id: str | None = None
    if body.chat_id is not None:
        chat = await session.get(Chat, body.chat_id)
        if chat is None or chat.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
        # A chat's selection applies only to the exact credential selected for this run.
        if chat.provider_credential_id == credential.id and chat.model_provider == credential.provider:
            conversation_model_id = chat.model_name

    config = resolve_request_config(
        provider=credential.provider,
        credential_id=credential.id,
        request_model_id=body.model_id,
        conversation_model_id=conversation_model_id,
        credential_default_model_id=credential.default_model_id,
        application_fallback_model_id=settings.groq_fallback_model,
        temperature=body.temperature,
        max_output_tokens=body.max_output_tokens,
    )

    structured_output: StructuredOutputSpec | None = None
    if body.structured_output is not None:
        if config.model_id not in STRICT_STRUCTURED_OUTPUT_MODELS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selected model does not support strict structured output",
            )
        try:
            structured_output = StructuredOutputSpec.create(
                name=body.structured_output.name,
                schema=body.structured_output.schema_,
            )
        except StructuredOutputError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    api_key = decrypt_secret(credential.encrypted_secret)
    provider = GroqProvider()
    try:
        available_models = await provider.list_models(api_key=api_key)
        if config.model_id not in {model.id for model in available_models}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selected model is not available for this Groq credential",
            )
        completion = await provider.complete(
            api_key=api_key,
            config=config,
            message=body.message,
            end_user_id=user.id,
            structured_output=structured_output,
        )
    except GroqProviderError as exc:
        raise _groq_error(exc) from exc
    return completion, config
