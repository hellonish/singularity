from engine.llm.openrouter import OPENROUTER_BASE_URL, OpenRouterProvider
from engine.llm.providers import DEFAULT_MODEL_BY_PROVIDER, provider_for


def test_openrouter_is_registered_with_its_openai_compatible_endpoint() -> None:
    provider = provider_for("openrouter")

    assert isinstance(provider, OpenRouterProvider)
    assert provider.base_url == OPENROUTER_BASE_URL
    assert provider.provider == "openrouter"
    assert DEFAULT_MODEL_BY_PROVIDER["openrouter"] == "openai/gpt-4.1-mini"


def test_openrouter_catalog_model_supplies_prompt_budget_limits() -> None:
    class CatalogModel:
        id = "anthropic/claude-test"
        owned_by = "anthropic"
        model_extra = {
            "context_length": 200_000,
            "top_provider": {"max_completion_tokens": 8_192},
        }

    model = OpenRouterProvider._catalog_model(CatalogModel())

    assert model.context_window == 200_000
    assert model.max_completion_tokens == 8_192
