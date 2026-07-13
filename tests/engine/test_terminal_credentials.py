from __future__ import annotations

import asyncio

from engine.cli.models import TerminalSession
from engine.cli.repl import EngineREPL, load_terminal_session
from engine.cli.settings import TerminalSettings
from engine.llm.groq import GroqModel


class FakeSettingsStore:
    def __init__(self, settings: TerminalSettings | None = None) -> None:
        self.settings = settings or TerminalSettings()

    def load(self):
        return self.settings

    def save(self, settings):
        self.settings = settings


class FakeProvider:
    display_name = "Fake"

    async def list_models(self, *, api_key):
        if api_key == "invalid":
            raise AssertionError("invalid test key")
        return [GroqModel(id="openai/gpt-oss-20b")]

    async def retrieve_model(self, *, api_key, model_id):
        return GroqModel(id=model_id, context_window=8192, max_completion_tokens=1024, active=True)


def test_terminal_session_loads_global_config(monkeypatch) -> None:
    session = load_terminal_session(FakeSettingsStore(TerminalSettings(
        api_keys={"deepseek": "saved-key", "groq": "another-key"}, selected_provider="deepseek", model="deepseek-v4-flash", effort="high",
    )))

    assert session.api_key == "saved-key"
    assert session.credential_source == "global_config"
    assert session.provider == "deepseek"
    assert session.model_id == "deepseek-v4-flash"


def test_terminal_session_does_not_read_provider_key_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-secret")

    session = load_terminal_session(FakeSettingsStore())

    assert session.api_key == ""
    assert session.credential_source == "none"


def test_key_setup_validates_then_persists_without_displaying_secret(capsys) -> None:
    store = FakeSettingsStore()
    repl = EngineREPL(TerminalSession(provider="deepseek"), settings_store=store, provider_factory=lambda _: FakeProvider())

    async def prompt_secret(message):
        return "new-secret"

    repl.ui.prompt_secret = prompt_secret
    asyncio.run(repl._set_key())

    assert store.settings.api_keys["deepseek"] == "new-secret"
    assert repl.session.api_key == "new-secret"
    assert repl.session.credential_source == "global_config"
    assert "new-secret" not in capsys.readouterr().out


def test_chat_is_blocked_until_a_key_is_configured(capsys) -> None:
    repl = EngineREPL(TerminalSession(), settings_store=FakeSettingsStore(), provider_factory=lambda _: FakeProvider())

    asyncio.run(repl._send("hello"))

    assert "Use /key first" in capsys.readouterr().out


def test_models_command_uses_interactive_selection(capsys) -> None:
    repl = EngineREPL(
        TerminalSession(api_key="saved-key", credential_source="global_config"),
        settings_store=FakeSettingsStore(),
        provider_factory=lambda _: FakeProvider(),
    )

    async def choose(**kwargs):
        assert kwargs["title"] == "Select Fake model"
        return "openai/gpt-oss-20b"

    repl.ui.choose = choose
    asyncio.run(repl._choose_model())

    assert repl.session.model_id == "openai/gpt-oss-20b"
    assert "Model selected" in capsys.readouterr().out


def test_provider_switch_restores_that_providers_saved_key_and_default_model() -> None:
    store = FakeSettingsStore(TerminalSettings(
        api_keys={"groq": "groq-key", "deepseek": "deepseek-key"},
        models={"groq": "custom-groq", "deepseek": "deepseek-v4-pro"},
        selected_provider="groq",
        model="openai/gpt-oss-20b",
        effort="medium",
    ))
    repl = EngineREPL(
        TerminalSession(api_key="groq-key", credential_source="global_config"),
        settings_store=store,
    )

    async def choose(**kwargs):
        return "deepseek"

    repl.ui.choose = choose
    asyncio.run(repl._choose_provider())

    assert repl.session.provider == "deepseek"
    assert repl.session.api_key == "deepseek-key"
    assert repl.session.model_id == "deepseek-v4-pro"
    assert store.settings.api_keys == {"groq": "groq-key", "deepseek": "deepseek-key"}


def test_openrouter_key_and_model_are_retained_independently() -> None:
    store = FakeSettingsStore(TerminalSettings(
        api_keys={"groq": "groq-key", "openrouter": "router-key"},
        models={"groq": "custom-groq", "openrouter": "anthropic/claude-3.5-haiku"},
    ))
    repl = EngineREPL(TerminalSession(api_key="groq-key"), settings_store=store)

    async def choose(**kwargs):
        return "openrouter"

    repl.ui.choose = choose
    asyncio.run(repl._choose_provider())

    assert repl.session.provider == "openrouter"
    assert repl.session.api_key == "router-key"
    assert repl.session.model_id == "anthropic/claude-3.5-haiku"
