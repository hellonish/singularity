"""OpenRouter's OpenAI-compatible provider adapter."""
from __future__ import annotations

from engine.llm.groq import GroqModel, GroqProvider, GroqProviderError

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


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
        max_completion_tokens = top_provider.get("max_completion_tokens")
        if context_window and not max_completion_tokens:
            max_completion_tokens = min(4_096, max(64, int(context_window) // 4))
        return GroqModel(
            id=str(getattr(model, "id")),
            owned_by=getattr(model, "owned_by", None),
            context_window=int(context_window) if context_window else None,
            max_completion_tokens=int(max_completion_tokens) if max_completion_tokens else None,
            active=True,
        )


OpenRouterProviderError = GroqProviderError
