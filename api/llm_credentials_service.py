"""
Load and validate user LLM API keys (BYOK) for chat and research.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.chat.models import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL_ID,
    MODEL_MAP,
    ModelInfo,
)
from api.llm_secret_crypto import decrypt_llm_secret, encrypt_llm_secret, is_decrypt_error
from db.models import UserLlmCredential

ALLOWED_PROVIDERS: frozenset[str] = frozenset({"grok", "gemini", "deepseek"})

def normalize_provider(raw: str) -> str:
    p = raw.strip().lower()
    if p not in ALLOWED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Allowed: {', '.join(sorted(ALLOWED_PROVIDERS))}",
        )
    return p


def model_provider(model_id: str) -> str:
    info: ModelInfo | None = MODEL_MAP.get(model_id)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model_id: {model_id}",
        )
    return info.provider


def validate_model_id(model_id: str) -> str:
    mid = (model_id or "").strip() or DEFAULT_MODEL_ID
    if mid not in MODEL_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model_id: {mid}",
        )
    return mid


def last_four(secret: str) -> str:
    s = secret.strip()
    if len(s) <= 4:
        return "****"
    return s[-4:]


async def get_credential_row(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
) -> UserLlmCredential | None:
    result = await db.execute(
        select(UserLlmCredential).where(
            UserLlmCredential.user_id == user_id,
            UserLlmCredential.provider == provider,
        )
    )
    return result.scalar_one_or_none()


async def get_decrypted_provider_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
) -> str | None:
    row = await get_credential_row(db, user_id, provider)
    if row is None:
        return None
    try:
        return decrypt_llm_secret(row.encrypted_secret)
    except Exception as e:
        if is_decrypt_error(e):
            return None
        raise


def credential_row_to_public(row: UserLlmCredential) -> dict:
    try:
        plain = decrypt_llm_secret(row.encrypted_secret)
        lf = last_four(plain)
    except Exception:
        lf = "????"
    return {
        "id": row.id,
        "provider": row.provider,
        "label": row.label,
        "last_four": lf,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


async def list_credentials_public(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(UserLlmCredential)
        .where(UserLlmCredential.user_id == user_id)
        .order_by(UserLlmCredential.provider)
    )
    rows = list(result.scalars().all())
    return [credential_row_to_public(r) for r in rows]


async def upsert_credential(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
    secret: str,
    label: str | None,
) -> UserLlmCredential:
    secret = secret.strip()
    if len(secret) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key is too short",
        )
    enc = encrypt_llm_secret(secret)
    existing = await get_credential_row(db, user_id, provider)
    if existing:
        existing.encrypted_secret = enc
        existing.label = label
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        return existing
    row = UserLlmCredential(
        user_id=user_id,
        provider=provider,
        encrypted_secret=enc,
        label=label,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_credential(
    db: AsyncSession,
    user_id: uuid.UUID,
    provider: str,
) -> bool:
    row = await get_credential_row(db, user_id, provider)
    if row is None:
        return False
    await db.delete(row)
    await db.commit()
    return True


async def providers_with_valid_keys(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> frozenset[str]:
    """
    Return each allowed provider for which the user has a stored, decryptable secret.

    Used to filter chat model options: only providers with a saved key are listed.
    """
    out: set[str] = set()
    for prov in sorted(ALLOWED_PROVIDERS):
        k = await get_decrypted_provider_key(db, user_id, prov)
        if k:
            out.add(prov)
    return frozenset(out)


def chat_models_for_providers(providers_with_keys: frozenset[str]) -> list[ModelInfo]:
    """Registered chat models for providers the user has configured (BYOK)."""
    return [m for m in AVAILABLE_MODELS if m.provider in providers_with_keys]


async def require_provider_key_for_model(
    db: AsyncSession,
    user_id: uuid.UUID,
    model_id: str,
) -> str:
    """
    Return the decrypted API key for the chat model's provider.

    Raises:
        HTTPException: 400 if the user has no key for that provider.
    """
    mid = validate_model_id(model_id)
    prov = model_provider(mid)
    k = await get_decrypted_provider_key(db, user_id, prov)
    if not k:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Add your {prov} API key in Profile → LLM keys to use this model.",
        )
    return k
