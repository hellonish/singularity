"""OpenRouter's OpenAI-compatible provider adapter."""
from __future__ import annotations

from engine.llm.groq import GroqModel, GroqProvider, GroqProviderError

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Curated true output-token limits for models whose OpenRouter catalog entry
# omits `top_provider.max_completion_tokens` (it is frequently null). The
# provider's live value always takes precedence; this table is consulted only
# when the catalog reports nothing, and the context//4 heuristic is the final
# fallback. Keep matching by substring so provider-routed variants (e.g.
# ":free", ":beta", region suffixes) resolve to the same ceiling.
# Sources to re-verify when curating: OpenRouter model pages and the upstream
# provider docs (Anthropic / OpenAI / Google model cards).
_CURATED_MAX_COMPLETION_TOKENS: tuple[tuple[str, int], ...] = (
    ("anthropic/claude-haiku-4.5", 8_192),
    ("anthropic/claude-sonnet-4", 8_192),
    ("anthropic/claude-3.5-haiku", 8_192),
    ("anthropic/claude-3.5-sonnet", 8_192),
    ("anthropic/claude-3-opus", 4_096),
    ("openai/gpt-4o", 16_384),
    ("openai/gpt-4o-mini", 16_384),
    ("google/gemini-2.0-flash", 8_192),
    ("google/gemini-2.5-flash", 8_192),
    ("google/gemini-2.5-pro", 8_192),
)

# The live OpenRouter catalog currently advertises ``response_format`` for
# this model, but its routed completion returned a JSON array in a research
# planner request on 2026-07-14. Research requires a JSON *object* at every
# stage, so keep it out of the selector until the provider route is reliable.
# This exception applies only to OpenRouter; the Groq-hosted model has a
# separate capability path.
_RESEARCH_UNRELIABLE_MODELS = frozenset({"openai/gpt-oss-20b"})


def _curated_max_completion_tokens(model_id: str) -> int | None:
    normalized = model_id.lower()
    for prefix, limit in _CURATED_MAX_COMPLETION_TOKENS:
        if normalized.startswith(prefix):
            return limit
    return None


class OpenRouterProvider(GroqProvider):
    """Stateless OpenRouter adapter for its normalized OpenAI Chat API."""

    provider = "openrouter"
    base_url = OPENROUTER_BASE_URL
    display_name = "OpenRouter"
    max_output_parameter = "max_tokens"

    async def list_models(self, *, api_key: str) -> list[GroqModel]:
        """Use OpenRouter's catalog, which includes usable context/output limits."""
        try:
            from openai import AsyncOpenAI

            async with AsyncOpenAI(api_key=api_key, base_url=self.base_url) as client:
                page = await client.models.list()
        except Exception as exc:
            raise self._classify_error(exc, operation="retrieve models") from exc
        return sorted((self._catalog_model(item) for item in page.data), key=lambda model: model.id)

    async def retrieve_model(self, *, api_key: str, model_id: str) -> GroqModel:
        # OpenRouter documents the catalog endpoint as the source for model
        # properties. Unlike Groq's API, `/models/{id}` is not a model-detail
        # endpoint, so selecting through that route yields a 404.
        for model in await self.list_models(api_key=api_key):
            if model.id == model_id:
                return model
        raise GroqProviderError(
            code="provider_request_rejected",
            message=f"OpenRouter model is not available in the current catalog: {model_id}",
            retryable=False,
        )

    @staticmethod
    def _catalog_model(model: object) -> GroqModel:
        extra = getattr(model, "model_extra", None) or {}
        top_provider = extra.get("top_provider") or {}
        context_window = extra.get("context_length") or top_provider.get("context_length")
        model_id = str(getattr(model, "id"))
        supported_parameters = {str(item) for item in extra.get("supported_parameters") or []}
        # Precedence: the provider's live limit, then a curated per-model value,
        # then a conservative context-derived heuristic. Only the live value is
        # authoritative; the rest keep effort budgets from being silently
        # clipped when OpenRouter reports no completion limit.
        max_completion_tokens = top_provider.get("max_completion_tokens")
        if not max_completion_tokens:
            max_completion_tokens = _curated_max_completion_tokens(model_id)
        if not max_completion_tokens and context_window:
            max_completion_tokens = min(4_096, max(64, int(context_window) // 4))
        return GroqModel(
            id=model_id,
            owned_by=getattr(model, "owned_by", None),
            context_window=int(context_window) if context_window else None,
            max_completion_tokens=int(max_completion_tokens) if max_completion_tokens else None,
            active=True,
            # Research requests response_format=json_object and asks OpenRouter
            # to route only to endpoints that honor every requested parameter.
            supports_research=(
                "response_format" in supported_parameters
                and model_id.lower() not in _RESEARCH_UNRELIABLE_MODELS
            ),
        )


OpenRouterProviderError = GroqProviderError
