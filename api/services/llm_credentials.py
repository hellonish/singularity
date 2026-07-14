from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.credential_crypto import encrypt_secret, fingerprint_secret
from api.models import LLMProviderCredential, User
from api.schemas import ProviderCredentialCreate, ProviderCredentialUpdate


_ACTIVE_CREDENTIAL_PROFILE_KEY = "active_provider_credential_id"


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


async def selected_credential_id(session: AsyncSession, user: User) -> str | None:
    """Return the user's selected active credential, never a stale/disabled one."""

    credential_id = (user.profile_data or {}).get(_ACTIVE_CREDENTIAL_PROFILE_KEY)
    if not isinstance(credential_id, str):
        return None
    try:
        await get_credential(session, user.id, credential_id)
    except HTTPException:
        return None
    return credential_id


async def select_credential(
    session: AsyncSession,
    user: User,
    credential_id: str | None,
) -> str | None:
    """Persist a user's execution credential without exposing its secret."""

    if credential_id is not None:
        await get_credential(session, user.id, credential_id)
    profile_data = dict(user.profile_data or {})
    if credential_id is None:
        profile_data.pop(_ACTIVE_CREDENTIAL_PROFILE_KEY, None)
    else:
        profile_data[_ACTIVE_CREDENTIAL_PROFILE_KEY] = credential_id
    # Assign a fresh mapping so SQLAlchemy reliably records JSON changes.
    user.profile_data = profile_data
    await session.commit()
    await session.refresh(user)
    return credential_id
