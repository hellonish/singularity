"""Provider selection and the common terminal/provider contract."""
from __future__ import annotations

from typing import Literal, Protocol

from engine.llm.deepseek import DeepSeekProvider
from engine.llm.groq import GroqProvider
from engine.llm.openrouter import OpenRouterProvider

ProviderName = Literal["groq", "deepseek", "openrouter"]
DEFAULT_MODEL_BY_PROVIDER: dict[ProviderName, str] = {
    "groq": "openai/gpt-oss-20b",
    "deepseek": "deepseek-v4-flash",
    "openrouter": "openai/gpt-4.1-mini",
}


class LLMProvider(Protocol):
    provider: str
    display_name: str

    async def list_models(self, *, api_key: str): ...
    async def retrieve_model(self, *, api_key: str, model_id: str): ...
    async def stream_chat(self, *, api_key: str, config, messages): ...
    async def complete(self, *, api_key: str, config, message: str, end_user_id: str, structured_output=None): ...
    async def stream_with_tools(self, *, api_key: str, config, messages, tools, end_user_id=None): ...


def provider_for(name: str) -> LLMProvider:
    if name == "groq":
        return GroqProvider()
    if name == "deepseek":
        return DeepSeekProvider()
    if name == "openrouter":
        return OpenRouterProvider()
    raise ValueError(f"Unsupported provider: {name}")
