"""
Encrypt/decrypt user LLM API keys at rest (Fernet symmetric).

Uses ``Settings.llm_credentials_encryption_key`` when set; in ``development``
with an empty key, derives a deterministic key from ``jwt_secret`` so local
dev works without a separate env var (not for production).
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from api.config import settings


def _fernet_key_material() -> bytes:
    raw = (settings.llm_credentials_encryption_key or "").strip()
    if raw:
        return raw.encode("utf-8")
    if settings.environment == "development":
        digest = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)
    raise RuntimeError(
        "LLM_CREDENTIALS_ENCRYPTION_KEY is required when ENVIRONMENT is not development"
    )


def _fernet() -> Fernet:
    return Fernet(_fernet_key_material())


def encrypt_llm_secret(plaintext: str) -> str:
    """Return url-safe token string to store in the database."""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_llm_secret(token: str) -> str:
    """Decrypt DB token; raises InvalidToken on tampering or wrong key."""
    return _fernet().decrypt(token.encode("ascii")).decode("utf-8")


def is_decrypt_error(exc: BaseException) -> bool:
    return isinstance(exc, InvalidToken)
