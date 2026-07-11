"""Encryption boundary for user-supplied provider credentials."""
from __future__ import annotations

import hashlib

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from api.config import settings


def _fernet() -> Fernet:
    if not settings.credential_encryption_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credential storage is not configured",
        )
    try:
        return Fernet(settings.credential_encryption_key.encode())
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credential storage is misconfigured",
        ) from exc


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored credential cannot be decrypted",
        ) from exc


def fingerprint_secret(secret: str) -> str:
    """A non-secret identifier useful for distinguishing stored credentials."""

    return hashlib.sha256(secret.encode()).hexdigest()
