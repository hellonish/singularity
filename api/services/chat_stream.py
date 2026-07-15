"""Request-scoped bridge from a persisted chat to the unified chat agent loop.

This mirrors ``api/research_runtime.py``: it resolves the chat's BYOK
credential, decrypts the key only in memory, builds the engine request config,
and streams the real agent. The plaintext key never leaves this call, and no
provider key or model object is persisted.
"""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.credential_crypto import decrypt_secret
from api.models import Chat, LLMProviderCredential, Message
from api.services import chats as chat_service
from api.services.llm_credentials import get_credential
from api.services.report_context_errors import ReportContextError
from api.services.retrieval import RetrievalService, TenantVectorStore
from api.vector_runtime import get_vector_store
from engine.chat.agent_loop import UnifiedChatAgentLoop
from engine.chat.effort import (
    ChatEffort,
    get_chat_effort_profile,
    provider_output_budget,
    reasoning_effort_for_model,
)
from engine.chat.models import ChatAgentInput, ChatStreamEvent
from engine.llm import provider_for, resolve_request_config
from engine.llm.config import LLMRequestConfig
from vector_store import DocumentChunk


_APPLICATION_FALLBACK = {
    "groq": lambda: settings.groq_fallback_model,
    "deepseek": lambda: settings.deepseek_fallback_model,
    "openrouter": lambda: settings.openrouter_fallback_model,
}

logger = logging.getLogger(__name__)

# How many report chunks to pull as chat context for a report-linked chat.
_REPORT_CONTEXT_LIMIT = 6


def _format_context(history: list[Message]) -> str:
    """Flatten prior turns into plain text for ChatAgentInput.context.

    The engine budgeter trims this to fit the model window, so we simply pass
    recent turns as labelled lines. The just-created user message is excluded by
    the caller.
    """
    lines: list[str] = []
    for message in history:
        if message.role not in {"user", "assistant"}:
            continue
        speaker = "User" if message.role == "user" else "Assistant"
        lines.append(f"{speaker}: {message.content}")
    return "\n".join(lines)


def _format_report_context(chunks: list[DocumentChunk]) -> str:
    """Render retrieved report chunks as a labelled context block.

    Kept distinct from conversational history so the model can tell attached
    report material from prior turns. Empty when nothing was retrieved.
    """
    passages = [chunk.text.strip() for chunk in chunks if chunk.text.strip()]
    if not passages:
        return ""
    body = "\n\n".join(passages)
    return f"Attached report context:\n{body}"


async def _retrieve_report_context(
    session: AsyncSession,
    chat: Chat,
    query: str,
    vector_store: TenantVectorStore,
) -> str:
    """Pull context for the chat's attached report, scoped to this user+report.

    Returns an empty string when the chat has no report attached. Retrieval is
    authorization-first: ``RetrievalService.search_report`` re-checks report
    ownership before constructing the ``{user_id, report_id}`` vector scope, so
    only this report's chunks (and never another report's or user's) are pulled.
    """
    if chat.report_id is None:
        return ""
    retrieval = RetrievalService(session=session, vector_store=vector_store)
    try:
        chunks = await retrieval.search_report(
            user_id=chat.user_id,
            report_id=chat.report_id,
            query=query,
            limit=_REPORT_CONTEXT_LIMIT,
        )
    except HTTPException:
        # Ownership failure (e.g. the report was deleted) is authoritative;
        # surface it rather than dropping the attachment.
        raise
    except Exception as exc:
        # A report-linked chat must not answer without its report — that would
        # produce confidently wrong replies. Log the real cause for operators
        # and fail the turn with a generic, retryable load message.
        logger.error(
            "report context retrieval failed for chat=%s report=%s user=%s: %s",
            chat.id,
            chat.report_id,
            chat.user_id,
            exc,
            exc_info=True,
        )
        raise ReportContextError() from exc
    return _format_report_context(chunks)


async def _resolve_config(
    session: AsyncSession,
    chat: Chat,
    effort: ChatEffort,
) -> tuple[LLMProviderCredential, LLMRequestConfig]:
    """Resolve the chat's credential and a clamped request config for one call.

    Raises ``HTTPException`` (422) if the chat has no active provider
    credential, so callers can fail before any streaming begins.
    """
    if chat.provider_credential_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Chat has no provider credential; connect a BYOK key before streaming",
        )
    credential = await get_credential(session, chat.user_id, chat.provider_credential_id)

    conversation_model_id = (
        chat.model_name if chat.model_provider == credential.provider else None
    )
    profile = get_chat_effort_profile(effort)
    config = resolve_request_config(
        provider=credential.provider,
        credential_id=credential.id,
        request_model_id=None,
        conversation_model_id=conversation_model_id,
        credential_default_model_id=credential.default_model_id,
        application_fallback_model_id=_APPLICATION_FALLBACK[credential.provider](),
        temperature=0.3,
        max_output_tokens=profile.max_output_tokens,
    )
    return credential, LLMRequestConfig(
        provider=config.provider,
        credential_id=config.credential_id,
        model_id=config.model_id,
        temperature=config.temperature,
        # The agent loop resolves live model capabilities before generation and
        # clamps this effort ceiling against the actual selected model.
        max_output_tokens=config.max_output_tokens,
        reasoning_effort=reasoning_effort_for_model(config.model_id, effort),
    )


async def build_stream(
    session: AsyncSession,
    chat: Chat,
    user_message: Message,
    *,
    vector_store: TenantVectorStore | None = None,
) -> tuple[AsyncIterator[ChatStreamEvent], LLMRequestConfig]:
    """Resolve the credential + config and return the engine event stream.

    Raises ``HTTPException`` (422) before any streaming begins if the chat has
    no active provider credential, so the caller never opens an SSE stream it
    cannot fulfill.
    """
    raw_effort = user_message.message_data.get("effort", ChatEffort.MEDIUM.value)
    try:
        effort = ChatEffort(str(raw_effort))
    except ValueError:
        effort = ChatEffort.MEDIUM
    credential, config = await _resolve_config(session, chat, effort)

    history = await chat_service.list_messages(session, chat)
    prior = [message for message in history if message.id != user_message.id]

    # A report-linked chat carries the report as retrieved context in addition
    # to prior turns, so each reply has both the conversation and the report.
    # The vector store is resolved lazily so a report-less chat never touches it.
    report_context = ""
    if chat.report_id is not None:
        report_context = await _retrieve_report_context(
            session, chat, user_message.content, vector_store or get_vector_store()
        )
    history_context = _format_context(prior)
    context = "\n\n".join(section for section in (report_context, history_context) if section)

    agent_input = ChatAgentInput(
        context=context,
        message=user_message.content,
    )

    api_key = decrypt_secret(credential.encrypted_secret)
    runtime = UnifiedChatAgentLoop(provider=provider_for(credential.provider))
    return runtime.stream(
        agent_input,
        api_key=api_key,
        config=config,
        effort=effort,
        modal_enabled=os.getenv("SINGULARITY_MODAL_ENABLED", "0") == "1",
    ), config


_TITLE_PROMPT = (
    "Write a title of 3 to 4 words for the conversation below. "
    "Reply with only the title itself: no quotes, no trailing punctuation, no explanation.\n\n"
    "User: {user}\n\nAssistant: {assistant}"
)

# Keep the title request cheap: the transcript excerpt is capped and the
# output budget is minimal (provider_output_budget still reserves reasoning
# room on reasoning models, where a tiny visible budget would starve the title).
_TITLE_TRANSCRIPT_CHARS = 1_500
_TITLE_OUTPUT_TOKENS = 60


def _sanitize_title(raw: str, fallback: str) -> str:
    """Reduce a model reply to one short title line, or fall back."""
    first_line = raw.strip().splitlines()[0] if raw.strip() else ""
    title = " ".join(first_line.strip().strip("\"'`").rstrip(".").split())
    words = title.split(" ")
    if len(words) > 6:
        title = " ".join(words[:6])
    return title[:80] or fallback


async def generate_chat_title(session: AsyncSession, chat: Chat, user_text: str, assistant_text: str) -> str:
    """Name the chat from its first exchange and persist the result.

    Never raises: a provider or credential failure falls back to a trimmed
    excerpt of the user's message so the sidebar always gets a real title.
    """
    fallback = " ".join(user_text.split())[:60] or "New chat"
    title = fallback
    try:
        credential, config = await _resolve_config(session, chat, ChatEffort.INSTANT)
        config = LLMRequestConfig(
            provider=config.provider,
            credential_id=config.credential_id,
            model_id=config.model_id,
            temperature=config.temperature,
            max_output_tokens=provider_output_budget(
                config.provider, config.model_id, _TITLE_OUTPUT_TOKENS
            ),
            reasoning_effort=reasoning_effort_for_model(config.model_id, ChatEffort.INSTANT),
        )
        api_key = decrypt_secret(credential.encrypted_secret)
        provider = provider_for(credential.provider)
        completion = await provider.complete(
            api_key=api_key,
            config=config,
            message=_TITLE_PROMPT.format(
                user=user_text[:_TITLE_TRANSCRIPT_CHARS],
                assistant=assistant_text[:_TITLE_TRANSCRIPT_CHARS],
            ),
            end_user_id=chat.user_id,
        )
        title = _sanitize_title(completion.content, fallback)
    except Exception as exc:
        logger.warning("chat title generation failed for chat=%s: %s", chat.id, exc)
    # This runs inside the SSE generator, after the request dependency scope
    # closed the session and detached ``chat``. The session object itself is
    # still usable, so persist through a freshly loaded instance instead of
    # touching the detached one.
    persisted = await chat_service.get_chat(session, chat.user_id, chat.id)
    persisted.title = title
    await session.commit()
    return title
