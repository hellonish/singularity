"""DeepSeek's OpenAI-compatible provider adapter."""
from __future__ import annotations

from engine.llm.groq import GroqProvider, GroqProviderError

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(GroqProvider):
    """Stateless DeepSeek adapter with the same bounded request surface as Groq."""

    provider = "deepseek"
    base_url = DEEPSEEK_BASE_URL
    display_name = "DeepSeek"


# The common error contract intentionally has provider-neutral codes. Keep a
# named alias so callers can catch a DeepSeek-specific import when useful.
DeepSeekProviderError = GroqProviderError
