from engine.llm.model_catalog import known_structured_output_support
from engine.llm.openrouter import OpenRouterProvider


def test_json_native_providers_are_always_capable_without_a_lookup():
    assert known_structured_output_support("groq", "any/model") is True
    assert known_structured_output_support("deepseek", "deepseek-v4-flash") is True


def test_curated_openrouter_models_resolve_offline():
    assert known_structured_output_support("openrouter", "anthropic/claude-haiku-4.5") is True
    # Prefix match covers routed variants (":free", region suffixes, etc.).
    assert known_structured_output_support("openrouter", "anthropic/claude-haiku-4.5:free") is True
    # Known-unreliable route is curated as unsupported.
    assert known_structured_output_support("openrouter", "openai/gpt-oss-20b") is False


def test_unknown_model_returns_none_so_live_detection_still_runs():
    assert known_structured_output_support("openrouter", "some-vendor/brand-new") is None


def test_curated_answer_wins_even_when_catalog_omits_supported_parameters():
    # A curated model with NO ``supported_parameters`` in the catalog would
    # otherwise be judged unsupported; the datastore answers True with no
    # dependence on that field being present.
    class CatalogModel:
        id = "anthropic/claude-haiku-4.5"
        owned_by = "anthropic"
        model_extra = {
            "context_length": 200_000,
            "top_provider": {"max_completion_tokens": 8_192},
        }

    assert OpenRouterProvider._catalog_model(CatalogModel()).supports_research is True
