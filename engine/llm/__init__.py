"""Request-scoped LLM provider integrations."""

from engine.llm.config import LLMRequestConfig
from engine.llm.deepseek import DeepSeekProvider
from engine.llm.groq import GroqProvider
from engine.llm.openrouter import OpenRouterProvider
from engine.llm.providers import DEFAULT_MODEL_BY_PROVIDER, LLMProvider, ProviderName, provider_for
from engine.llm.selection import resolve_request_config
from engine.llm.structured import StructuredOutputSpec

__all__ = [
    "DEFAULT_MODEL_BY_PROVIDER", "DeepSeekProvider", "GroqProvider", "LLMProvider", "OpenRouterProvider",
    "LLMRequestConfig", "ProviderName", "StructuredOutputSpec", "provider_for", "resolve_request_config",
]
