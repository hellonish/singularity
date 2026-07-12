from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMRequestConfig:
    """Immutable model settings resolved for exactly one LLM request/run.

    Deliberately contains a credential ID rather than a secret. The provider
    receives a decrypted API key only as a method argument for the duration of
    its API call.
    """

    provider: str
    credential_id: str
    model_id: str
    temperature: float = 0.3
    max_output_tokens: int = 1500
    reasoning_effort: str | None = None
