from __future__ import annotations

from fastapi import APIRouter

from api.config import settings
from api.schemas import StorageHealthRead

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/health", response_model=StorageHealthRead)
async def storage_health() -> StorageHealthRead:
    """Configuration-level check; provider-specific readiness can be added later."""

    return StorageHealthRead(status="ok", backend=settings.storage_backend)
