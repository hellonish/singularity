from __future__ import annotations

import json
import os
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from engine.chat.effort import ChatEffort, get_chat_effort_profile
from engine.cli.api_client import SingularityAPIClient, SingularityAPIError
from engine.cli.banner import COMMANDS, LOGO
from engine.cli.models import TerminalSession
from engine.cli.settings import DEFAULT_MODEL_BY_PROVIDER, GlobalTerminalSettingsStore, TerminalSettings
from engine.cli.ui import TerminalUI


class EngineREPL:
    """Async prompt-toolkit REPL with Rich output for terminal chat."""

    def __init__(
        self,
        session: TerminalSession,
        *,
        settings_store: GlobalTerminalSettingsStore | None = None,
        provider_factory: Callable[[str], object] | None = None,
        api_client: SingularityAPIClient | None = None,
        ui: TerminalUI | None = None,
    ) -> None:
        self.session = session
        self._settings_store = settings_store or GlobalTerminalSettingsStore()
        self._provider_factory = provider_factory
        self._api_client = api_client or SingularityAPIClient(self._settings_store)
        # This checkout is a direct terminal runtime by default.  An API
        # backend is opt-in because a local .env (including Modal settings)
        # must never be silently ignored.
        self._use_hosted_api = os.getenv("SINGULARITY_CLI_BACKEND", "local").lower() == "api"
        self._api_chat_id: str | None = None
        self._agents: dict[str, object] = {}
        if not self._use_hosted_api:
            from engine.cli.agents import ChatTerminalAgent

            chat = ChatTerminalAgent()
            self._agents[chat.name] = chat
        self.ui = ui or TerminalUI(session_state=self._session_state)

    def _local_provider(self):
        if self._provider_factory is not None:
            return self._provider_factory(self.session.provider)
        from engine.llm.providers import provider_for

        return provider_for(self.session.provider)

    def _session_state(self) -> dict[str, str]:
        return {
            "agent": self.session.agent_name,
            "provider": self.session.provider,
            "model": self.session.model_id,
            "effort": str(self.session.effort),
            "key": "saved" if self.session.api_key else "missing",
            "backend": "api" if self._use_hosted_api else "local",
        }

    async def run(self) -> int:
        self.ui.banner(
            logo=LOGO,
            agent=self.session.agent_name,
            model=self.session.model_id,
            effort=str(self.session.effort),
            key_configured=bool(self.session.api_key),
            modal_enabled=os.getenv("SINGULARITY_MODAL_ENABLED", "0") == "1",
            api_backed=self._use_hosted_api,
            provider=self.session.provider.title(),
        )
        if not self.session.api_key:
            self.ui.warning("No API key is saved. Use /key to configure one before chatting.")
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
        elif command == "/provider":
            await self._choose_provider()
        elif command == "/effort":
            await self._choose_effort()
        elif command == "/mode":
            await self._choose_mode()
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

    async def _research_live(self, query: str) -> None:
        """Run hosted bounded research so end users need no worker or Modal setup."""
        if not self._use_hosted_api:
            await self._research_local(query)
            return
        self.ui.start_status("Connecting to hosted bounded research…")
        try:
            strength = {
                ChatEffort.INSTANT: 1,
                ChatEffort.MEDIUM: 2,
                ChatEffort.HIGH: 3,
                ChatEffort.ULTRA: 3,
            }[self.session.effort]
            credential_id = await self._api_client.ensure_credential(
                provider=self.session.provider,
                api_key=self.session.api_key,
                model_id=self.session.model_id,
            )
            run = await self._api_client.create_research_run(
                query=query,
                credential_id=credential_id,
                model_id=self.session.model_id,
                strength=strength,
            )
            async for event in self._api_client.stream_research(str(run["id"])):
                if event.event == "research.progress":
                    self.ui.render_research_progress(event.data)
                elif event.event == "research.phase":
                    details = event.data.get("details")
                    if isinstance(details, list) and details and isinstance(details[-1], dict):
                        self.ui.render_research_progress(details[-1])
                elif event.event == "research.failed":
                    raise SingularityAPIError(str(event.data.get("error") or "Research failed"))
                elif event.event == "research.cancelled":
                    raise SingularityAPIError("Research was cancelled")
            report = ""
            async for event in self._api_client.stream_report(str(run["report_id"])):
                if event.event == "report.delta":
                    report += str(event.data.get("delta") or "")
                elif event.event == "report.completed" and not report:
                    report = str(event.data.get("content") or "")
                elif event.event == "report.pending":
                    raise SingularityAPIError("Research completed but its report is not ready")
            if not report:
                raise SingularityAPIError("Research completed without a report")
        except Exception as exc:
            self.ui.stop_status()
            self.ui.error(f"Live research failed: {type(exc).__name__}: {exc}")
            return
        self.ui.stop_status()
        self.ui.answer(report)

    async def _research_local(self, query: str) -> None:
        """Run the direct local research path."""
        from engine.research_workflow.runner import run_research

        self.ui.start_status("Running local bounded LangGraph research…")
        try:
            strength = {
                ChatEffort.INSTANT: 1,
                ChatEffort.MEDIUM: 2,
                ChatEffort.HIGH: 3,
                ChatEffort.ULTRA: 3,
            }[self.session.effort]
            report = await run_research(
                query=query,
                strength=strength,
                output_dir=Path(".artifacts/research"),
                api_key=self.session.api_key,
                provider_name=self.session.provider,
                model_id=self.session.model_id,
                on_progress=self.ui.render_research_progress,
            )
        except Exception as exc:
            self.ui.stop_status()
            self.ui.error(f"Local research failed: {type(exc).__name__}: {exc}")
            self.ui.info("Diagnostics: .artifacts/research/latest-research-diagnostics.jsonl")
            return
        self.ui.stop_status()
        self.ui.answer(report)

    async def _choose_mode(self) -> None:
        selected = await self.ui.choose(
            title="Select mode",
            text="Research uses the hosted Singularity workflow; Chat streams through the same API.",
            values=[
                ("chat", "Chat      Persistent selected-provider conversation through the API"),
                ("research", "Research  Live bounded LangGraph workflow with sourced web evidence"),
            ],
            default=self.session.agent_name,
        )
        if selected is None:
            return
        self.session.agent_name = selected
        self.ui.info(f"Mode selected: {selected}. Your next plain-text prompt will use {selected} mode.")

    def _require_key(self) -> bool:
        if self.session.api_key:
            return True
        self.ui.error(f"No {self.session.provider.title()} API key is configured. Use /key first.")
        return False

    async def _choose_model(self) -> None:
        from engine.chat.model_capabilities import MODEL_CAPABILITIES
        if not self._require_key():
            return
        use_direct_provider = not self._use_hosted_api or self._provider_factory is not None
        display_name = self.session.provider.title()
        provider = self._local_provider() if use_direct_provider else None
        if provider is not None:
            display_name = provider.display_name
        self.ui.start_status(f"Loading {display_name} models…")
        try:
            if provider is not None:
                models = await provider.list_models(api_key=self.session.api_key)
                MODEL_CAPABILITIES.remember_available(
                    f"local:{self.session.provider}", self.session.provider, models
                )
                # Only offer models that support structured outputs: every
                # research stage and the API's strict-output path depend on it.
                model_ids = [model.id for model in models if model.supports_research]
            else:
                remote_models = await self._api_client.list_models(
                    provider=self.session.provider,
                    api_key=self.session.api_key,
                    model_id=self.session.model_id,
                )
                model_ids = [
                    str(model["id"]) for model in remote_models if model.get("supports_research")
                ]
        except Exception as exc:
            self.ui.stop_status()
            self.ui.error(f"Could not load models: {getattr(exc, 'message', str(exc))}")
            return
        self.ui.stop_status()
        selected = await self.ui.choose(
            title=f"Select {display_name} model",
            text="Use ↑/↓ to choose a model and Enter to confirm.",
            values=[(model_id, model_id) for model_id in model_ids],
            default=self.session.model_id if self.session.model_id in model_ids else None,
        )
        if selected is None:
            return
        if provider is not None:
            self.ui.start_status("Validating model…")
            try:
                model = await provider.retrieve_model(api_key=self.session.api_key, model_id=selected)
            except Exception as exc:
                self.ui.stop_status()
                self.ui.error(f"Could not select model: {getattr(exc, 'message', str(exc))}")
                return
            self.ui.stop_status()
            if not model.active:
                self.ui.error(f"Model is inactive: {model.id}")
                return
            self.session.model_id = model.id
            self.session.model_max_completion_tokens = model.max_completion_tokens
            if model.context_window and model.max_completion_tokens:
                MODEL_CAPABILITIES.remember(self.session.provider, model)
        else:
            self.session.model_id = selected
            self.session.model_max_completion_tokens = None
        self._api_chat_id = None
        self._save_settings()
        self.ui.info(f"Model selected: {self.session.model_id}")

    async def _choose_provider(self) -> None:
        selected = await self.ui.choose(
            title="Select LLM provider",
            text="Changing provider uses that provider's saved key and default model.",
            values=[
                ("deepseek", "DeepSeek    OpenAI-compatible DeepSeek API"),
                ("openrouter", "OpenRouter  Multi-provider OpenAI-compatible API"),
                ("groq", "Groq        Groq API"),
            ],
            default=self.session.provider,
        )
        if selected is None or selected == self.session.provider:
            return
        settings = self._settings_store.load()
        self.session.provider = selected
        self.session.model_id = settings.models.get(selected, DEFAULT_MODEL_BY_PROVIDER[selected])
        # The new provider's model hasn't been retrieved yet, so its live output
        # ceiling is unknown until the user reselects a model.
        self.session.model_max_completion_tokens = None
        self.session.api_key = settings.api_keys.get(selected, "")
        self.session.credential_source = "global_config" if self.session.api_key else "none"
        self._api_chat_id = None
        self._save_settings()
        self.ui.info(f"Provider selected: {selected}; model is {self.session.model_id}.")

    async def _choose_effort(self) -> None:
        if self.session.agent_name == "research":
            await self._choose_research_depth()
            return
        profiles = [get_chat_effort_profile(effort) for effort in ChatEffort]
        selected = await self.ui.choose(
            title="Select chat effort",
            text="Higher effort allows more context, tool steps, output, and execution time.",
            values=[
                (
                    profile.effort,
                    f"{profile.effort.value.title():7}  {profile.max_agent_tool_steps} steps · "
                    f"{profile.max_tool_actions} actions · {profile.max_parallel_actions} parallel · "
                    f"{profile.max_output_tokens:,} output tokens",
                )
                for profile in profiles
            ],
            default=self.session.effort,
        )
        if selected is None:
            return
        self.session.apply_effort(selected)
        self._save_settings()
        profile = get_chat_effort_profile(self.session.effort)
        self.ui.info(
            f"Effort selected: {self.session.effort} "
            f"(steps={profile.max_agent_tool_steps}, actions={profile.max_tool_actions}, "
            f"parallel={profile.max_parallel_actions}, output={profile.max_output_tokens:,})"
        )

    async def _choose_research_depth(self) -> None:
        from engine.research_workflow.caps import RunCaps, format_runtime_seconds

        depths = [
            (ChatEffort.INSTANT, "Quick", 1),
            (ChatEffort.MEDIUM, "Standard", 2),
            (ChatEffort.HIGH, "Deep", 3),
        ]
        values = []
        for effort, label, strength in depths:
            caps = RunCaps.for_strength(strength)
            values.append((
                effort,
                f"{label:8} {caps.qa_cycles} QA cycle(s) · {caps.max_nodes} nodes · "
                f"{format_runtime_seconds(caps.llm_step_timeout_seconds)} per model step · "
                f"{format_runtime_seconds(caps.max_runtime_seconds)} run max",
            ))
        default = self.session.effort
        if default is ChatEffort.ULTRA:
            default = ChatEffort.HIGH
        selected = await self.ui.choose(
            title="Select research depth",
            text="Choose the bounded research graph size and maximum runtime.",
            values=values,
            default=default,
        )
        if selected is None:
            return
        self.session.apply_effort(selected)
        self._save_settings()
        strength = {
            ChatEffort.INSTANT: 1,
            ChatEffort.MEDIUM: 2,
            ChatEffort.HIGH: 3,
        }[self.session.effort]
        caps = RunCaps.for_strength(strength)
        label = {1: "quick", 2: "standard", 3: "deep"}[strength]
        self.ui.info(
            f"Research depth selected: {label} "
            f"({caps.qa_cycles} QA cycle(s), {caps.max_nodes} nodes, "
            f"{format_runtime_seconds(caps.llm_step_timeout_seconds)} per model step, "
            f"{format_runtime_seconds(caps.max_runtime_seconds)} run max)"
        )

    async def _manage_key(self) -> None:
        action = await self.ui.choose(
            title=f"{self.session.provider.title()} API key",
            text="The key is stored in your private global Singularity config file (mode 0600), never in the repository.",
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
            self.ui.info(f"{self.session.provider.title()} key: {status}; source={self.session.credential_source}")
        elif action == "remove":
            confirmed = await self.ui.choose(
                title=f"Remove {self.session.provider.title()} API key",
                text="This removes the selected provider's key from your global Singularity configuration.",
                values=[(False, "Cancel"), (True, "Remove saved key")],
                default=False,
            )
            if not confirmed:
                return
            self.session.api_key = ""
            self.session.credential_source = "none"
            self._api_chat_id = None
            self._save_settings()
            self.ui.info(f"Saved {self.session.provider.title()} key removed.")

    async def _set_key(self) -> None:
        try:
            api_key = (await self.ui.prompt_secret(f"{self.session.provider.title()} API key: ")).strip()
        except (EOFError, KeyboardInterrupt):
            self.ui.info("Key setup cancelled.")
            return
        if not api_key:
            self.ui.error(f"{self.session.provider.title()} API key cannot be empty.")
            return
        use_direct_provider = not self._use_hosted_api or self._provider_factory is not None
        provider = self._local_provider() if use_direct_provider else None
        display_name = provider.display_name if provider is not None else self.session.provider.title()
        self.ui.start_status(f"Validating {display_name} key…")
        try:
            if provider is not None:
                await provider.list_models(api_key=api_key)
            else:
                await self._api_client.list_models(
                    provider=self.session.provider,
                    api_key=api_key,
                    model_id=self.session.model_id,
                )
        except Exception as exc:
            self.ui.stop_status()
            self.ui.error(f"{display_name} key was not saved: {getattr(exc, 'message', str(exc))}")
            return
        self.ui.stop_status()
        self.session.api_key = api_key
        self.session.credential_source = "global_config"
        self._api_chat_id = None
        self._save_settings()
        self.ui.info(f"{display_name} key validated and saved in the global configuration.")

    def _status(self) -> None:
        modal = "enabled" if os.getenv("SINGULARITY_MODAL_ENABLED", "0") == "1" else "disabled"
        langsmith = "enabled" if os.getenv("LANGSMITH_TRACING", "false").lower() in {"1", "true", "yes"} else "disabled"
        self.ui.table(title="Session status", rows=[
            ("Agent", self.session.agent_name),
            ("Provider", self.session.provider),
            ("Model", self.session.model_id),
            ("Effort", str(self.session.effort)),
            ("API key", f"{'configured' if self.session.api_key else 'missing'} ({self.session.credential_source})"),
            ("Backend", "hosted API" if self._use_hosted_api else "local developer mode"),
            ("API URL", self._api_client.base_url if self._use_hosted_api else "n/a"),
            ("History turns", str(len(self.session.history))),
            ("Modal tools", "server-managed" if self._use_hosted_api else modal),
            ("LangSmith", langsmith),
            ("Max output tokens", str(self.session.max_output_tokens)),
        ])

    def _reset(self) -> None:
        self.session.history.clear()
        self.session.compacted_summary = None
        self.session.compacted_through = 0
        self._api_chat_id = None
        self.ui.info("Conversation history reset.")

    async def _send(self, message: str) -> None:
        if self.session.agent_name == "research":
            if not self._require_key():
                return
            await self._research_live(message)
            return
        if not self._require_key():
            return
        if self._use_hosted_api:
            await self._send_api(message)
            return
        await self._send_local(message)

    async def _send_api(self, message: str) -> None:
        """Stream one persisted chat turn through the hosted API."""
        buffered = ""
        self.ui.start_status("Connecting to Singularity API…")
        try:
            if self._api_chat_id is None:
                credential_id = await self._api_client.ensure_credential(
                    provider=self.session.provider,
                    api_key=self.session.api_key,
                    model_id=self.session.model_id,
                )
                self._api_chat_id = await self._api_client.create_chat(
                    credential_id=credential_id,
                    model_id=self.session.model_id,
                )
            async for event in self._api_client.stream_chat(
                chat_id=self._api_chat_id,
                message=message,
                effort=self.session.effort.value,
            ):
                if event.event == "message.accepted":
                    self.ui.render_lifecycle(kind="model_started", content="")
                elif event.event == "message.progress":
                    self.ui.render_lifecycle(
                        kind=str(event.data.get("kind") or "metadata"),
                        content=str(event.data.get("message") or ""),
                        elapsed_seconds=(
                            float(event.data["elapsed_seconds"])
                            if event.data.get("elapsed_seconds") is not None
                            else None
                        ),
                    )
                elif event.event == "message.delta":
                    delta = str(event.data.get("delta") or "")
                    if delta:
                        self.ui.stop_status()
                        buffered += delta
                        self.ui.stream_delta(delta)
                elif event.event == "message.completed" and not buffered:
                    buffered = str(event.data.get("content") or "")
                elif event.event == "message.error":
                    raise SingularityAPIError(
                        str(event.data.get("message") or "The model request failed"),
                        code=str(event.data.get("code") or "") or None,
                    )
            self.ui.stop_status()
            self.ui.final_answer(buffered)
        except Exception as exc:
            self.ui.stop_status()
            if buffered:
                self.ui.final_answer(buffered)
            self.ui.error(f"API request failed: {exc}")

    async def _send_local(self, message: str) -> None:
        """Developer-only direct provider/Modal path."""
        agent = self._agents[self.session.agent_name]
        buffered = ""
        run_id = uuid4().hex
        diagnostics_path = Path(".artifacts/research/latest-chat-diagnostics.jsonl")
        diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostics_path.write_text("", encoding="utf-8")

        def record(event: dict) -> None:
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                **event,
            }
            with diagnostics_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")

        record({
            "phase": "chat",
            "status": "started",
            "provider": self.session.provider,
            "model": self.session.model_id,
            "effort": str(self.session.effort),
        })
        try:
            async for output in agent.stream(message=message, session=self.session):  # type: ignore[attr-defined]
                if output.kind != "delta":
                    record({
                        "phase": "chat",
                        "status": output.kind,
                        "message": output.content[:300],
                        "elapsed_seconds": output.elapsed_seconds,
                    })
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
            record({"phase": "chat", "status": "completed"})
        except (TimeoutError, ValueError) as exc:
            record({
                "phase": "chat",
                "status": "failed",
                "error_type": type(exc).__name__,
                "provider_code": getattr(exc, "code", None),
                "message": str(exc)[:500],
            })
            self.ui.stop_status()
            if buffered:
                self.ui.final_answer(buffered)
            self.ui.error(f"Agent failed: {exc}")
            self.ui.info("Diagnostics: .artifacts/research/latest-chat-diagnostics.jsonl")

    def _save_settings(self) -> None:
        existing = self._settings_store.load()
        api_keys = dict(existing.api_keys)
        models = dict(existing.models)
        if self.session.api_key:
            api_keys[self.session.provider] = self.session.api_key
        else:
            api_keys.pop(self.session.provider, None)
        models[self.session.provider] = self.session.model_id
        self._settings_store.save(TerminalSettings(
            api_keys=api_keys,
            models=models,
            selected_provider=self.session.provider,
            model=self.session.model_id,
            effort=self.session.effort.value,
            api_device_token=existing.api_device_token,
            api_refresh_token=existing.api_refresh_token,
        ))


def load_terminal_session(settings_store: GlobalTerminalSettingsStore | None = None) -> TerminalSession:
    settings = (settings_store or GlobalTerminalSettingsStore()).load()
    return TerminalSession(
        api_key=settings.api_keys.get(settings.selected_provider, ""),
        credential_source="global_config" if settings.api_keys.get(settings.selected_provider) else "none",
        provider=settings.selected_provider,
        model_id=settings.models.get(settings.selected_provider, settings.model),
        effort=ChatEffort(settings.effort),
    )
