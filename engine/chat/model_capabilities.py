"""Cached, credential-safe model capability lookup for chat requests."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Protocol

from engine.llm.groq import GroqModel


class ModelLookupProvider(Protocol):
    async def retrieve_model(self, *, api_key: str, model_id: str) -> GroqModel: ...


@dataclass(frozen=True)
class ModelCapabilities:
    provider: str
    model_id: str
    context_window: int
    max_completion_tokens: int
    active: bool
    supports_research: bool
    fetched_at: float

    def as_model(self) -> GroqModel:
        return GroqModel(
            id=self.model_id,
            context_window=self.context_window,
            max_completion_tokens=self.max_completion_tokens,
            active=self.active,
            supports_research=self.supports_research,
        )


class ModelCapabilityRegistry:
    """Metadata-only cache; API keys are accepted transiently and never stored."""

    def __init__(self, *, ttl_seconds: float = 6 * 60 * 60) -> None:
        self._ttl_seconds = ttl_seconds
        self._caps: dict[tuple[str, str], ModelCapabilities] = {}
        self._available_by_credential: dict[str, frozenset[tuple[str, str]]] = {}
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}

    def get(self, provider: str, model_id: str) -> ModelCapabilities | None:
        caps = self._caps.get((provider, model_id))
        if caps is None or monotonic() - caps.fetched_at >= self._ttl_seconds:
            return None
        return caps

    def remember(self, provider: str, model: GroqModel) -> ModelCapabilities:
        if not model.context_window or not model.max_completion_tokens:
            raise ValueError(f"model {model.id} did not report usable token limits")
        caps = ModelCapabilities(
            provider=provider,
            model_id=model.id,
            context_window=int(model.context_window),
            max_completion_tokens=int(model.max_completion_tokens),
            active=bool(model.active),
            supports_research=bool(model.supports_research),
            fetched_at=monotonic(),
        )
        self._caps[(provider, model.id)] = caps
        return caps

    def remember_available(
        self,
        credential_id: str,
        provider: str,
        models: list[GroqModel],
    ) -> frozenset[tuple[str, str]]:
        available = frozenset((provider, model.id) for model in models if model.active)
        self._available_by_credential[credential_id] = available
        return available

    def is_available(self, credential_id: str, provider: str, model_id: str) -> bool:
        return (provider, model_id) in self._available_by_credential.get(credential_id, frozenset())

    async def resolve(
        self,
        *,
        provider_name: str,
        provider: ModelLookupProvider,
        api_key: str,
        model_id: str,
    ) -> ModelCapabilities:
        cached = self.get(provider_name, model_id)
        if cached is not None:
            return cached
        key = (provider_name, model_id)
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self.get(provider_name, model_id)
            if cached is not None:
                return cached
            model = await provider.retrieve_model(api_key=api_key, model_id=model_id)
            return self.remember(provider_name, model)

    def clear(self) -> None:
        self._caps.clear()
        self._available_by_credential.clear()
        self._locks.clear()


MODEL_CAPABILITIES = ModelCapabilityRegistry()
