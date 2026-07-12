from __future__ import annotations

import asyncio

from engine.cli.models import TerminalSession
from engine.cli.repl import EngineREPL, load_terminal_session
from engine.llm.groq import GroqModel


class FakeCredentialStore:
    def __init__(self, key: str | None = None) -> None:
        self.key = key

    def get_groq_key(self):
        return self.key

    def set_groq_key(self, api_key):
        self.key = api_key

    def delete_groq_key(self):
        self.key = None


class FakeProvider:
    async def list_models(self, *, api_key):
        if api_key == "invalid":
            raise AssertionError("invalid test key")
        return [GroqModel(id="openai/gpt-oss-20b")]

    async def retrieve_model(self, *, api_key, model_id):
        return GroqModel(id=model_id, context_window=8192, max_completion_tokens=1024, active=True)


def test_terminal_session_loads_global_system_credential(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("SINGULARITY_TEST_GROQ_API_KEY", raising=False)

    session = load_terminal_session(FakeCredentialStore("saved-key"))

    assert session.api_key == "saved-key"
    assert session.credential_source == "system"


def test_terminal_session_does_not_read_groq_key_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "environment-secret")

    session = load_terminal_session(FakeCredentialStore())

    assert session.api_key == ""
    assert session.credential_source == "none"


def test_key_setup_validates_then_persists_without_displaying_secret(capsys) -> None:
    store = FakeCredentialStore()
    repl = EngineREPL(TerminalSession(), credential_store=store, provider=FakeProvider())

    async def prompt_secret(message):
        return "new-secret"

    repl.ui.prompt_secret = prompt_secret
    asyncio.run(repl._set_key())

    assert store.key == "new-secret"
    assert repl.session.api_key == "new-secret"
    assert repl.session.credential_source == "system"
    assert "new-secret" not in capsys.readouterr().out


def test_chat_is_blocked_until_a_key_is_configured(capsys) -> None:
    repl = EngineREPL(TerminalSession(), credential_store=FakeCredentialStore(), provider=FakeProvider())

    asyncio.run(repl._send("hello"))

    assert "Use /key first" in capsys.readouterr().out


def test_models_command_uses_interactive_selection(capsys) -> None:
    repl = EngineREPL(
        TerminalSession(api_key="saved-key", credential_source="system"),
        credential_store=FakeCredentialStore("saved-key"),
        provider=FakeProvider(),
    )

    async def choose(**kwargs):
        assert kwargs["title"] == "Select Groq model"
        return "openai/gpt-oss-20b"

    repl.ui.choose = choose
    asyncio.run(repl._choose_model())

    assert repl.session.model_id == "openai/gpt-oss-20b"
    assert "Model selected" in capsys.readouterr().out
