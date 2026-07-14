"""Request-scoped orchestration between persisted BYOK credentials and providers."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.credential_crypto import decrypt_secret
from api.config import settings
from api.models import Chat, User
from api.schemas import LLMCompletionCreate
from api.services.llm_credentials import get_credential
from api.services.llm_errors import provider_error as _groq_error
from engine.chat.effort import provider_output_budget
from engine.llm import provider_for, resolve_request_config
from engine.llm.config import LLMRequestConfig
from engine.llm.groq import GroqProviderError, GroqModel, LLMCompletion
from engine.llm.structured import STRICT_STRUCTURED_OUTPUT_MODELS, StructuredOutputError, StructuredOutputSpec


async def list_models(
    session: AsyncSession,
    user: User,
    credential_id: str,
) -> list[GroqModel]:
    credential = await get_credential(session, user.id, credential_id)
    api_key = decrypt_secret(credential.encrypted_secret)
    try:
        return await provider_for(credential.provider).list_models(api_key=api_key)
    except GroqProviderError as exc:
        raise _groq_error(exc) from exc


async def complete(
    session: AsyncSession,
    user: User,
    body: LLMCompletionCreate,
) -> tuple[LLMCompletion, object]:
    credential = await get_credential(session, user.id, body.provider_credential_id)
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
        application_fallback_model_id={
            "groq": settings.groq_fallback_model,
            "deepseek": settings.deepseek_fallback_model,
            "openrouter": settings.openrouter_fallback_model,
        }[credential.provider],
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
    provider = provider_for(credential.provider)
    try:
        available_models = await provider.list_models(api_key=api_key)
        selected_model = next((m for m in available_models if m.id == config.model_id), None)
        if selected_model is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Selected model is not available for this Groq credential",
            )
        # Clamp the caller-requested budget to the provider/model limit, using the
        # model's live ceiling when the catalog exposes it (else static fallback).
        config = LLMRequestConfig(
            provider=config.provider,
            credential_id=config.credential_id,
            model_id=config.model_id,
            temperature=config.temperature,
            max_output_tokens=provider_output_budget(
                config.provider,
                config.model_id,
                config.max_output_tokens,
                model_max_completion_tokens=selected_model.max_completion_tokens,
            ),
            reasoning_effort=config.reasoning_effort,
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
