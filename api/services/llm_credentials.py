from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.credential_crypto import encrypt_secret, fingerprint_secret
from api.models import LLMProviderCredential, User
from api.schemas import ProviderCredentialCreate, ProviderCredentialUpdate


async def get_credential(
    session: AsyncSession,
    user_id: str,
    credential_id: str,
    *,
    require_active: bool = True,
) -> LLMProviderCredential:
    result = await session.execute(
        select(LLMProviderCredential).where(
            LLMProviderCredential.id == credential_id,
            LLMProviderCredential.user_id == user_id,
        )
    )
    credential = result.scalar_one_or_none()
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider credential not found")
    if require_active and credential.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Provider credential is disabled")
    return credential


async def list_credentials(session: AsyncSession, user_id: str) -> list[LLMProviderCredential]:
    result = await session.execute(
        select(LLMProviderCredential)
        .where(LLMProviderCredential.user_id == user_id)
        .order_by(LLMProviderCredential.created_at.desc())
    )
    return list(result.scalars())


async def create_credential(
    session: AsyncSession,
    user: User,
    body: ProviderCredentialCreate,
) -> LLMProviderCredential:
    secret = body.api_key.get_secret_value()
    credential = LLMProviderCredential(
        user_id=user.id,
        provider=body.provider,
        label=body.label,
        encrypted_secret=encrypt_secret(secret),
        key_fingerprint=fingerprint_secret(secret),
        default_model_id=body.default_model_id,
    )
    session.add(credential)
    await session.commit()
    await session.refresh(credential)
    return credential


async def update_credential(
    session: AsyncSession,
    credential: LLMProviderCredential,
    body: ProviderCredentialUpdate,
) -> LLMProviderCredential:
    if body.label is not None:
        credential.label = body.label
    if "default_model_id" in body.model_fields_set:
        credential.default_model_id = body.default_model_id
    if body.status is not None:
        credential.status = body.status
    await session.commit()
    await session.refresh(credential)
    return credential
