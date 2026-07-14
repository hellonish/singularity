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
            "supported_parameters": ["max_tokens", "response_format"],
        }

    model = OpenRouterProvider._catalog_model(CatalogModel())

    assert model.context_window == 200_000
    assert model.max_completion_tokens == 8_192
    assert model.supports_research is True


def test_openrouter_catalog_excludes_models_without_json_output_support() -> None:
    class CatalogModel:
        id = "anthropic/claude-3-haiku"
        owned_by = "anthropic"
        model_extra = {
            "context_length": 200_000,
            "top_provider": {"max_completion_tokens": 4_096},
            "supported_parameters": ["max_tokens", "temperature"],
        }

    assert OpenRouterProvider._catalog_model(CatalogModel()).supports_research is False


def test_openrouter_catalog_excludes_known_unreliable_json_object_route() -> None:
    class CatalogModel:
        id = "openai/gpt-oss-20b"
        owned_by = "openai"
        model_extra = {
            "context_length": 131_072,
            "top_provider": {"max_completion_tokens": 8_192},
            "supported_parameters": ["max_tokens", "response_format"],
        }

    # This OpenRouter route returned a JSON array for a json_object research
    # request, which cannot satisfy the planner's object contract.
    assert OpenRouterProvider._catalog_model(CatalogModel()).supports_research is False


def test_live_max_completion_tokens_wins_over_curated_table() -> None:
    class CatalogModel:
        id = "anthropic/claude-haiku-4.5"
        owned_by = "anthropic"
        model_extra = {
            "context_length": 200_000,
            "top_provider": {"max_completion_tokens": 4_096},
        }

    model = OpenRouterProvider._catalog_model(CatalogModel())

    # The provider's live value is authoritative even when a curated entry exists.
    assert model.max_completion_tokens == 4_096


def test_curated_table_fills_missing_completion_limit() -> None:
    class CatalogModel:
        id = "anthropic/claude-haiku-4.5"
        owned_by = "anthropic"
        model_extra = {
            "context_length": 200_000,
            "top_provider": {"max_completion_tokens": None},
        }

    model = OpenRouterProvider._catalog_model(CatalogModel())

    # 200_000 // 4 would clip to the 4_096 heuristic; the curated 8_192 wins.
    assert model.max_completion_tokens == 8_192


def test_heuristic_fallback_when_model_is_uncurated() -> None:
    class CatalogModel:
        id = "some-vendor/unknown-model"
        owned_by = "some-vendor"
        model_extra = {"context_length": 32_000, "top_provider": {}}

    model = OpenRouterProvider._catalog_model(CatalogModel())

    assert model.max_completion_tokens == 4_096  # min(4_096, 32_000 // 4)
