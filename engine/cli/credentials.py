"""OS-backed credential persistence for the terminal application."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import keyring
from keyring.errors import KeyringError

SERVICE_NAME = "Singularity"
GROQ_ACCOUNT = "groq-api-key"


class CredentialStoreError(RuntimeError):
    """Safe credential-store failure without secret contents."""


class CredentialStore(Protocol):
    def get_groq_key(self) -> str | None: ...
    def set_groq_key(self, api_key: str) -> None: ...
    def delete_groq_key(self) -> None: ...


@dataclass(frozen=True)
class SystemCredentialStore:
    """Persist credentials in macOS Keychain / Windows Vault / Secret Service."""

    service_name: str = SERVICE_NAME
    account_name: str = GROQ_ACCOUNT

    def get_groq_key(self) -> str | None:
        try:
            return keyring.get_password(self.service_name, self.account_name)
        except KeyringError as exc:
            raise CredentialStoreError("The operating-system credential store is unavailable") from exc

    def set_groq_key(self, api_key: str) -> None:
        if not api_key.strip():
            raise ValueError("Groq API key cannot be empty")
        try:
            keyring.set_password(self.service_name, self.account_name, api_key.strip())
        except KeyringError as exc:
            raise CredentialStoreError("Could not save the key in the operating-system credential store") from exc

    def delete_groq_key(self) -> None:
        try:
            keyring.delete_password(self.service_name, self.account_name)
        except keyring.errors.PasswordDeleteError:
            return
        except KeyringError as exc:
            raise CredentialStoreError("Could not remove the key from the operating-system credential store") from exc
