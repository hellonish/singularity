from __future__ import annotations

from fastapi import APIRouter, Response, status

from api.dependencies import CurrentUserDep, SessionDep
from api.schemas import UserCreate, UserRead, UserUpdate
from api.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, session: SessionDep) -> UserRead:
    """Bootstrap a local development user; replace this with signup/auth later."""

    return await user_service.create_user(session, body)


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: CurrentUserDep) -> UserRead:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    body: UserUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserRead:
    return await user_service.update_user(session, current_user, body)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    await user_service.deactivate_user(session, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
