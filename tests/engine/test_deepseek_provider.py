from engine.llm.deepseek import DEEPSEEK_BASE_URL, DeepSeekProvider
from engine.llm.providers import DEFAULT_MODEL_BY_PROVIDER, provider_for


def test_deepseek_is_registered_with_its_openai_compatible_endpoint() -> None:
    provider = provider_for("deepseek")

    assert isinstance(provider, DeepSeekProvider)
    assert provider.base_url == DEEPSEEK_BASE_URL
    assert provider.provider == "deepseek"
    assert DEFAULT_MODEL_BY_PROVIDER["deepseek"] == "deepseek-v4-flash"
