from __future__ import annotations

from fastapi import APIRouter, Response, status

from api.dependencies import SessionDep
from api.schemas import CLIDeviceLoginRequest, GoogleLoginRequest, RefreshRequest, TokenPair
from api.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/cli-device", response_model=TokenPair)
async def cli_device_login(body: CLIDeviceLoginRequest, session: SessionDep) -> TokenPair:
    _user, access_token, refresh_token, expires_in = await auth_service.cli_device_login(
        session, body.device_token.get_secret_value()
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in)


@router.post("/google", response_model=TokenPair)
async def google_login(body: GoogleLoginRequest, session: SessionDep) -> TokenPair:
    _user, access_token, refresh_token, expires_in = await auth_service.google_login(session, body.id_token)
    return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, session: SessionDep) -> TokenPair:
    access_token, refresh_token, expires_in = await auth_service.refresh(session, body.refresh_token)
    return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, session: SessionDep) -> Response:
    await auth_service.logout(session, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
