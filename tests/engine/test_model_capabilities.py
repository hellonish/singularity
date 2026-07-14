import asyncio

from engine.chat.model_capabilities import ModelCapabilityRegistry
from engine.llm.groq import GroqModel


class Provider:
    def __init__(self) -> None:
        self.calls = 0

    async def retrieve_model(self, *, api_key: str, model_id: str) -> GroqModel:
        self.calls += 1
        return GroqModel(id=model_id, context_window=200_000, max_completion_tokens=64_000)


def test_model_capability_registry_resolves_once_then_uses_o1_lookup() -> None:
    registry = ModelCapabilityRegistry(ttl_seconds=60)
    provider = Provider()

    async def resolve_twice():
        first = await registry.resolve(
            provider_name="openrouter", provider=provider, api_key="secret", model_id="model"
        )
        second = await registry.resolve(
            provider_name="openrouter", provider=provider, api_key="different", model_id="model"
        )
        return first, second

    first, second = asyncio.run(resolve_twice())
    assert first is second
    assert provider.calls == 1
    assert registry.get("openrouter", "model") is first
    assert first.max_completion_tokens == 64_000


def test_model_availability_is_indexed_by_credential_without_storing_keys() -> None:
    registry = ModelCapabilityRegistry()
    models = [GroqModel(id="a"), GroqModel(id="b", active=False)]
    registry.remember_available("credential-1", "groq", models)

    assert registry.is_available("credential-1", "groq", "a") is True
    assert registry.is_available("credential-1", "groq", "b") is False
    assert registry.is_available("another-credential", "groq", "a") is False
