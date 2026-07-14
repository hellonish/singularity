from __future__ import annotations

import asyncio

from engine.cli.api_client import APIEvent
from engine.cli.models import TerminalSession
from engine.cli.repl import EngineREPL
from engine.cli.settings import TerminalSettings


class FakeSettingsStore:
    def __init__(self) -> None:
        self.settings = TerminalSettings()

    def load(self) -> TerminalSettings:
        return self.settings

    def save(self, settings: TerminalSettings) -> None:
        self.settings = settings


class FakeAPIClient:
    base_url = "https://api.test/api"

    def __init__(self) -> None:
        self.chat_creations = 0

    async def ensure_credential(self, **kwargs) -> str:
        assert kwargs["api_key"] == "byok"
        return "cred-1"

    async def create_chat(self, **kwargs) -> str:
        self.chat_creations += 1
        return "chat-1"

    async def stream_chat(self, **kwargs):
        yield APIEvent("message.accepted", {"model_id": "model-1"})
        yield APIEvent("message.delta", {"delta": "Hosted "})
        yield APIEvent("message.delta", {"delta": "answer"})
        yield APIEvent("message.completed", {"content": "Hosted answer"})

    async def create_research_run(self, **kwargs):
        return {"id": "run-1", "report_id": "report-1"}

    async def stream_research(self, run_id: str):
        yield APIEvent("research.progress", {"status": "node_started", "message": "Researching"})
        yield APIEvent("research.completed", {"status": "completed"})

    async def stream_report(self, report_id: str):
        yield APIEvent("report.delta", {"delta": "# Hosted report\n"})
        yield APIEvent("report.completed", {"content": "# Hosted report\n"})


def test_repl_uses_one_hosted_api_chat_for_multiple_turns(capsys, monkeypatch) -> None:
    monkeypatch.delenv("SINGULARITY_CLI_BACKEND", raising=False)
    api = FakeAPIClient()
    repl = EngineREPL(
        TerminalSession(api_key="byok"),
        settings_store=FakeSettingsStore(),
        api_client=api,  # type: ignore[arg-type]
    )

    asyncio.run(repl._send("first"))
    asyncio.run(repl._send("second"))

    assert api.chat_creations == 1
    assert capsys.readouterr().out.count("Hosted answer") == 2


def test_repl_streams_hosted_research_report_without_local_worker(capsys, monkeypatch) -> None:
    monkeypatch.delenv("SINGULARITY_CLI_BACKEND", raising=False)
    repl = EngineREPL(
        TerminalSession(api_key="byok", agent_name="research"),
        settings_store=FakeSettingsStore(),
        api_client=FakeAPIClient(),  # type: ignore[arg-type]
    )

    asyncio.run(repl._send("research this"))

    assert "Hosted report" in capsys.readouterr().out
