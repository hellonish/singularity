from __future__ import annotations

import os
import shlex
from pathlib import Path

from dotenv import load_dotenv

# Repo root (…/singularity), so the CLI loads the project .env regardless of the
# directory it is launched from. A relative "./.env" silently loaded nothing
# when invoked from elsewhere, leaving SINGULARITY_MODAL_* unset and falling
# back to the wrong Modal environment.
_REPO_ROOT = Path(__file__).resolve().parents[2]

from engine.chat.effort import ChatEffort, get_chat_effort_profile
from engine.cli.agents import ChatTerminalAgent, TerminalAgent
from engine.cli.banner import COMMANDS, LOGO
from engine.cli.credentials import CredentialStore, CredentialStoreError, SystemCredentialStore
from engine.cli.models import TerminalSession
from engine.cli.ui import TerminalUI
from engine.llm.groq import GroqProvider, GroqProviderError


class EngineREPL:
    """Async prompt-toolkit REPL with Rich output for terminal chat."""

    def __init__(
        self,
        session: TerminalSession,
        *,
        credential_store: CredentialStore | None = None,
        provider: GroqProvider | None = None,
        ui: TerminalUI | None = None,
    ) -> None:
        self.session = session
        self._provider = provider or GroqProvider()
        self._credential_store = credential_store or SystemCredentialStore()
        chat = ChatTerminalAgent(provider=self._provider)
        self._agents: dict[str, TerminalAgent] = {chat.name: chat}
        self.ui = ui or TerminalUI(session_state=self._session_state)

    def _session_state(self) -> dict[str, str]:
        return {
            "agent": self.session.agent_name,
            "model": self.session.model_id,
            "effort": str(self.session.effort),
            "key": "saved" if self.session.api_key else "missing",
        }

    async def run(self) -> int:
        self.ui.banner(
            logo=LOGO,
            agent=self.session.agent_name,
            model=self.session.model_id,
            effort=str(self.session.effort),
            key_configured=bool(self.session.api_key),
            modal_enabled=os.getenv("SINGULARITY_MODAL_ENABLED", "0") == "1",
        )
        if not self.session.api_key:
            self.ui.warning("No Groq API key is saved. Use /key to configure one before chatting.")
        while True:
            try:
                line = await self.ui.prompt()
            except KeyboardInterrupt:
                self.ui.info("Use /quit or Ctrl+C on an empty prompt to exit.")
                continue
            except EOFError:
                self.ui.stop_status()
                self.ui.console.print()
                return 0
            line = line.strip()
            if not line:
                continue
            if line.startswith("/"):
                if await self._command(line):
                    self.ui.stop_status()
                    return 0
            else:
                await self._send(line)

    async def _command(self, line: str) -> bool:
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            self.ui.error(f"Invalid command: {exc}")
            return False
        command, *args = parts
        if command == "/quit":
            return True
        if args:
            self.ui.error(f"{command} does not accept arguments; use its interactive selector.")
            return False
        if command == "/help":
            self.ui.help(list(COMMANDS))
        elif command == "/models":
            await self._choose_model()
        elif command == "/effort":
            await self._choose_effort()
        elif command == "/key":
            await self._manage_key()
        elif command == "/status":
            self._status()
        elif command == "/reset":
            self._reset()
        elif command == "/clear":
            self.ui.console.clear()
        else:
            self.ui.error(f"Unknown command: {command}. Type /help.")
        return False

    def _require_key(self) -> bool:
        if self.session.api_key:
            return True
        self.ui.error("No Groq API key is configured. Use /key first.")
        return False

    async def _choose_model(self) -> None:
        if not self._require_key():
            return
        self.ui.start_status("Loading Groq models…")
        try:
            models = await self._provider.list_models(api_key=self.session.api_key)
        except GroqProviderError as exc:
            self.ui.stop_status()
            self.ui.error(f"Could not load models: {exc.message}")
            return
        self.ui.stop_status()
        selected = await self.ui.choose(
            title="Select Groq model",
            text="Use ↑/↓ to choose a model and Enter to confirm.",
            values=[(model.id, model.id) for model in models],
            default=self.session.model_id if any(model.id == self.session.model_id for model in models) else None,
        )
        if selected is None:
            return
        self.ui.start_status("Validating model…")
        try:
            model = await self._provider.retrieve_model(api_key=self.session.api_key, model_id=selected)
        except GroqProviderError as exc:
            self.ui.stop_status()
            self.ui.error(f"Could not select model: {exc.message}")
            return
        self.ui.stop_status()
        if not model.active:
            self.ui.error(f"Model is inactive: {model.id}")
            return
        self.session.model_id = model.id
        self.ui.info(f"Model selected: {model.id}")

    async def _choose_effort(self) -> None:
        profiles = [get_chat_effort_profile(effort) for effort in ChatEffort]
        selected = await self.ui.choose(
            title="Select chat effort",
            text="Higher effort allows more context, tool steps, output, and execution time.",
            values=[
                (
                    profile.effort,
                    f"{profile.effort.value.title():7}  {profile.max_agent_tool_steps} step(s) · "
                    f"{profile.max_output_tokens:,} output tokens · {profile.timeout_seconds}s",
                )
                for profile in profiles
            ],
            default=self.session.effort,
        )
        if selected is None:
            return
        self.session.apply_effort(selected)
        profile = get_chat_effort_profile(self.session.effort)
        self.ui.info(
            f"Effort selected: {self.session.effort} "
            f"(output={profile.max_output_tokens:,}, timeout={profile.timeout_seconds}s)"
        )

    async def _manage_key(self) -> None:
        action = await self.ui.choose(
            title="Groq API key",
            text="The key is stored in your operating-system credential store, never in the repository.",
            values=[
                ("set", "Set or replace key"),
                ("status", "Show key status"),
                ("remove", "Remove saved key"),
            ],
            default="status" if self.session.api_key else "set",
        )
        if action == "set":
            await self._set_key()
        elif action == "status":
            status = "configured" if self.session.api_key else "not configured"
            self.ui.info(f"Groq key: {status}; source={self.session.credential_source}")
        elif action == "remove":
            confirmed = await self.ui.choose(
                title="Remove Groq API key",
                text="This removes the key saved for Singularity from the operating-system credential store.",
                values=[(False, "Cancel"), (True, "Remove saved key")],
                default=False,
            )
            if not confirmed:
                return
            try:
                self._credential_store.delete_groq_key()
            except CredentialStoreError as exc:
                self.ui.error(str(exc))
                return
            self.session.api_key = ""
            self.session.credential_source = "none"
            self.ui.info("Saved Groq key removed.")

    async def _set_key(self) -> None:
        try:
            api_key = (await self.ui.prompt_secret("Groq API key: ")).strip()
        except (EOFError, KeyboardInterrupt):
            self.ui.info("Key setup cancelled.")
            return
        if not api_key:
            self.ui.error("Groq API key cannot be empty.")
            return
        self.ui.start_status("Validating Groq key…")
        try:
            await self._provider.list_models(api_key=api_key)
        except GroqProviderError as exc:
            self.ui.stop_status()
            self.ui.error(f"Groq key was not saved: {exc.message}")
            return
        try:
            self._credential_store.set_groq_key(api_key)
        except (CredentialStoreError, ValueError) as exc:
            self.ui.stop_status()
            self.ui.error(str(exc))
            return
        self.ui.stop_status()
        self.session.api_key = api_key
        self.session.credential_source = "system"
        self.ui.info("Groq key validated and saved in the operating-system credential store.")

    def _status(self) -> None:
        modal = "enabled" if os.getenv("SINGULARITY_MODAL_ENABLED", "0") == "1" else "disabled"
        langsmith = "enabled" if os.getenv("LANGSMITH_TRACING", "false").lower() in {"1", "true", "yes"} else "disabled"
        self.ui.table(title="Session status", rows=[
            ("Agent", self.session.agent_name),
            ("Model", self.session.model_id),
            ("Effort", str(self.session.effort)),
            ("Groq key", f"{'configured' if self.session.api_key else 'missing'} ({self.session.credential_source})"),
            ("History turns", str(len(self.session.history))),
            ("Modal tools", modal),
            ("LangSmith", langsmith),
            ("Temperature", str(self.session.temperature)),
            ("Max output tokens", str(self.session.max_output_tokens)),
        ])

    def _reset(self) -> None:
        self.session.history.clear()
        self.session.compacted_summary = None
        self.session.compacted_through = 0
        self.ui.info("Conversation history reset.")

    async def _send(self, message: str) -> None:
        if not self._require_key():
            return
        agent = self._agents[self.session.agent_name]
        buffered = ""
        try:
            async for output in agent.stream(message=message, session=self.session):
                if output.kind == "delta":
                    self.ui.stop_status()
                    buffered += output.content
                    self.ui.stream_delta(output.content)
                else:
                    self.ui.render_lifecycle(
                        kind=output.kind,
                        content=output.content,
                        elapsed_seconds=output.elapsed_seconds,
                    )
            if buffered:
                self.ui.final_answer(buffered)
        except (GroqProviderError, TimeoutError, ValueError) as exc:
            self.ui.stop_status()
            if buffered:
                self.ui.final_answer(buffered)
            self.ui.error(f"Agent failed: {exc}")


def load_terminal_session(credential_store: CredentialStore | None = None) -> TerminalSession:
    load_dotenv(_REPO_ROOT / ".env")
    store = credential_store or SystemCredentialStore()
    try:
        saved_key = store.get_groq_key()
    except CredentialStoreError:
        saved_key = None
    if saved_key:
        return TerminalSession(api_key=saved_key, credential_source="system")
    return TerminalSession()
