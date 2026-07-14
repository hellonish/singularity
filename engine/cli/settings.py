"""Private, global terminal settings shared by every Singularity CLI launch."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from engine.chat.effort import ChatEffort

ProviderName = Literal["groq", "deepseek", "openrouter"]
DEFAULT_MODEL_BY_PROVIDER: dict[ProviderName, str] = {
    "groq": "openai/gpt-oss-20b",
    "deepseek": "deepseek-v4-flash",
    "openrouter": "openai/gpt-4.1-mini",
}

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "singularity" / "terminal.json"


@dataclass(frozen=True)
class TerminalSettings:
    api_keys: dict[str, str] = field(default_factory=dict)
    models: dict[str, str] = field(default_factory=dict)
    selected_provider: ProviderName = "groq"
    model: str = DEFAULT_MODEL_BY_PROVIDER["groq"]
    effort: str = ChatEffort.MEDIUM.value
    api_device_token: str = ""
    api_refresh_token: str = ""

    @classmethod
    def from_dict(cls, raw: object) -> "TerminalSettings":
        if not isinstance(raw, dict):
            return cls()
        provider = raw.get("selected_provider", "groq")
        if provider not in {"groq", "deepseek", "openrouter"}:
            provider = "groq"
        effort = raw.get("effort", ChatEffort.MEDIUM.value)
        try:
            effort = ChatEffort(effort).value
        except ValueError:
            effort = ChatEffort.MEDIUM.value
        model = raw.get("model")
        models = raw.get("models", {})
        if not isinstance(models, dict):
            models = {}
        if model and provider not in models:
            models[provider] = str(model)
        api_keys = raw.get("api_keys", {})
        if not isinstance(api_keys, dict):
            api_keys = {}
        # Accept the short-lived single-key format so existing users are not
        # locked out after upgrading to multi-provider settings.
        legacy_key = raw.get("api_key", "")
        if legacy_key and provider not in api_keys:
            api_keys[provider] = str(legacy_key)
        return cls(
            api_keys={name: str(key) for name, key in api_keys.items() if name in {"groq", "deepseek", "openrouter"} and key},
            models={name: str(value) for name, value in models.items() if name in {"groq", "deepseek", "openrouter"} and value},
            selected_provider=provider,
            model=str(models.get(provider) or DEFAULT_MODEL_BY_PROVIDER[provider]),
            effort=effort,
            api_device_token=str(raw.get("api_device_token") or ""),
            api_refresh_token=str(raw.get("api_refresh_token") or ""),
        )


class GlobalTerminalSettingsStore:
    """JSON settings file, permissioned to its owning user (0600)."""

    def __init__(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        self.path = path

    def load(self) -> TerminalSettings:
        try:
            return TerminalSettings.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return TerminalSettings()

    def save(self, settings: TerminalSettings) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)
        os.chmod(self.path, 0o600)
