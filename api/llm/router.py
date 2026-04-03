"""Public LLM model catalog for chat (BYOK)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.llm_credentials_service import chat_models_for_providers, providers_with_valid_keys
from db.models import User

router = APIRouter(prefix="/llm", tags=["llm"])


class LlmModelOut(BaseModel):
    model_id: str
    display_name: str
    provider: str
    tags: list[str]
    description: str


class LlmModelsResponse(BaseModel):
    models: list[LlmModelOut]


@router.get("/models", response_model=LlmModelsResponse)
async def list_llm_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LlmModelsResponse:
    """
    Chat models the current user can run with their stored keys only.

    Excludes models whose provider (or Grok, used by the thinker) has no key.
    """
    prov = await providers_with_valid_keys(db, current_user.id)
    eligible = chat_models_for_providers(prov)
    return LlmModelsResponse(
        models=[
            LlmModelOut(
                model_id=m.model_id,
                display_name=m.display_name,
                provider=m.provider,
                tags=list(m.tags),
                description=m.description,
            )
            for m in eligible
        ]
    )
