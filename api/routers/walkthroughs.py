from __future__ import annotations

from fastapi import APIRouter, Response, status

from api.dependencies import CurrentUserDep, SessionDep
from api.schemas import WalkthroughClaimRead, WalkthroughRequest
from api.services import walkthroughs as walkthrough_service

router = APIRouter(prefix="/walkthroughs", tags=["walkthroughs"])


@router.post("/{walkthrough_key}/claim", response_model=WalkthroughClaimRead)
async def claim_walkthrough(
    walkthrough_key: str,
    body: WalkthroughRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> WalkthroughClaimRead:
    """Atomically claim a walkthrough for the caller.

    ``show`` is true only for the single request that wins the claim; concurrent
    tabs/devices and already-seen users get ``show: false``.
    """
    show = await walkthrough_service.claim(
        session,
        user_id=current_user.id,
        walkthrough_key=walkthrough_key,
        version=body.version,
    )
    return WalkthroughClaimRead(show=show, walkthrough_key=walkthrough_key, version=body.version)


@router.post("/{walkthrough_key}/complete", status_code=status.HTTP_204_NO_CONTENT)
async def complete_walkthrough(
    walkthrough_key: str,
    body: WalkthroughRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    await walkthrough_service.complete(
        session,
        user_id=current_user.id,
        walkthrough_key=walkthrough_key,
        version=body.version,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{walkthrough_key}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_walkthrough(
    walkthrough_key: str,
    body: WalkthroughRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    await walkthrough_service.dismiss(
        session,
        user_id=current_user.id,
        walkthrough_key=walkthrough_key,
        version=body.version,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
