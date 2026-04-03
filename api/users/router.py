"""Users / Stats API router — profile, usage, analytics."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.llm_credentials_service import (
    credential_row_to_public,
    delete_credential,
    list_credentials_public,
    normalize_provider,
    upsert_credential,
)
from api.users.schemas import (
    DeviceBreakdownResponse,
    LlmCredentialDeleteResponse,
    LlmCredentialListResponse,
    LlmCredentialPublic,
    LlmCredentialPutBody,
    ModelBreakdownResponse,
    UsageSeriesResponse,
    UsageStats,
    UserProfile,
)
from api.users.service import (
    compute_stats,
    get_device_breakdown,
    get_model_breakdown,
    get_usage_series,
    get_user_profile,
)
from db.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    """Return the current authenticated user's profile."""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        daily_token_budget=current_user.daily_token_budget,
    )


@router.get("/me/stats", response_model=UsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageStats:
    """Aggregate usage statistics for the current user."""
    stats = await compute_stats(db, current_user.id)
    return UsageStats(**stats)


@router.get("/me/usage", response_model=UsageSeriesResponse)
async def get_usage(
    range: str = Query("30d", regex="^(7d|30d|90d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageSeriesResponse:
    """
    Daily usage time series for graphs.

    ``range`` can be 7d, 30d, or 90d.
    """
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map[range]
    data = await get_usage_series(db, current_user.id, days)
    return UsageSeriesResponse(**data)


@router.get("/me/usage/models", response_model=ModelBreakdownResponse)
async def get_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModelBreakdownResponse:
    """Token and cost breakdown by LLM model."""
    data = await get_model_breakdown(db, current_user.id)
    return ModelBreakdownResponse(**data)


@router.get("/me/usage/devices", response_model=DeviceBreakdownResponse)
async def get_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeviceBreakdownResponse:
    """Device, OS, and browser breakdown from usage events."""
    data = await get_device_breakdown(db, current_user.id)
    return DeviceBreakdownResponse(**data)


@router.get("/me/llm-credentials", response_model=LlmCredentialListResponse)
async def list_llm_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LlmCredentialListResponse:
    rows = await list_credentials_public(db, current_user.id)
    return LlmCredentialListResponse(
        credentials=[LlmCredentialPublic(**r) for r in rows]
    )


@router.put("/me/llm-credentials/{provider}", response_model=LlmCredentialPublic)
async def put_llm_credential(
    provider: str,
    body: LlmCredentialPutBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LlmCredentialPublic:
    prov = normalize_provider(provider)
    row = await upsert_credential(
        db, current_user.id, prov, body.secret, body.label
    )
    return LlmCredentialPublic(**credential_row_to_public(row))


@router.delete(
    "/me/llm-credentials/{provider}",
    response_model=LlmCredentialDeleteResponse,
    status_code=status.HTTP_200_OK,
)
async def remove_llm_credential(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LlmCredentialDeleteResponse:
    """
    Remove the current user's encrypted API key for ``provider`` (grok | gemini | deepseek).

    Returns 404 if no credential exists for that provider.
    """
    prov = normalize_provider(provider)
    ok = await delete_credential(db, current_user.id, prov)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No API key saved for this provider.",
        )
    return LlmCredentialDeleteResponse()
