from __future__ import annotations

from fastapi import APIRouter, status

from api.dependencies import CurrentUserDep, SessionDep
from api.schemas import (
    AvailableModelRead,
    LLMCompletionCreate,
    LLMCompletionRead,
    ProviderCredentialCreate,
    ProviderCredentialRead,
    ProviderCredentialSelectionRead,
    ProviderCredentialSelectionUpdate,
    ProviderCredentialUpdate,
)
from api.services import llm as llm_service
from api.services import llm_credentials as credential_service

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/credentials", response_model=list[ProviderCredentialRead])
async def list_credentials(session: SessionDep, current_user: CurrentUserDep) -> list[ProviderCredentialRead]:
    return await credential_service.list_credentials(session, current_user.id)


@router.post("/credentials", response_model=ProviderCredentialRead, status_code=status.HTTP_201_CREATED)
async def create_credential(
    body: ProviderCredentialCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ProviderCredentialRead:
    return await credential_service.create_credential(session, current_user, body)


@router.patch("/credentials/{credential_id}", response_model=ProviderCredentialRead)
async def update_credential(
    credential_id: str,
    body: ProviderCredentialUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ProviderCredentialRead:
    credential = await credential_service.get_credential(
        session, current_user.id, credential_id, require_active=False
    )
    return await credential_service.update_credential(session, credential, body)


@router.get("/selection", response_model=ProviderCredentialSelectionRead)
async def get_credential_selection(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ProviderCredentialSelectionRead:
    return ProviderCredentialSelectionRead(
        credential_id=await credential_service.selected_credential_id(session, current_user)
    )


@router.put("/selection", response_model=ProviderCredentialSelectionRead)
async def set_credential_selection(
    body: ProviderCredentialSelectionUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ProviderCredentialSelectionRead:
    return ProviderCredentialSelectionRead(
        credential_id=await credential_service.select_credential(session, current_user, body.credential_id)
    )


@router.get("/credentials/{credential_id}/models", response_model=list[AvailableModelRead])
async def list_available_models(
    credential_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[AvailableModelRead]:
    return await llm_service.list_models(session, current_user, credential_id)


@router.post("/completions", response_model=LLMCompletionRead)
async def create_completion(
    body: LLMCompletionCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> LLMCompletionRead:
    completion, config = await llm_service.complete(session, current_user, body)
    return LLMCompletionRead(
        provider=config.provider,
        credential_id=config.credential_id,
        model_id=config.model_id,
        content=completion.content,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
        structured_output=completion.structured_output,
    )
