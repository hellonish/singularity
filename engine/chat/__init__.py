"""Standalone streaming chat agent.

Attributes are exposed lazily so that importing a lightweight submodule
(e.g. ``engine.chat.effort``) does not eagerly pull in the Groq/OpenAI LLM
stack. This matters for the Modal tools container, which installs only the
tool dependencies and must not require ``openai`` just to reach ChatEffort
via ``engine.tools.contracts``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# (attribute, submodule) — resolved on first access via __getattr__.
_EXPORTS: dict[str, str] = {
    "ChatAgent": "engine.chat.agent",
    "ChatAgentInput": "engine.chat.models",
    "ChatStreamEvent": "engine.chat.models",
    "ContextSnapshot": "engine.chat.context",
    "UniversalContextPolicy": "engine.chat.context",
    "ChatEffort": "engine.chat.effort",
    "ChatEffortProfile": "engine.chat.effort",
    "get_chat_effort_profile": "engine.chat.effort",
}

__all__ = list(_EXPORTS)

if TYPE_CHECKING:  # keep static analysers / IDEs aware of the real symbols
    from engine.chat.agent import ChatAgent
    from engine.chat.context import ContextSnapshot, UniversalContextPolicy
    from engine.chat.effort import ChatEffort, ChatEffortProfile, get_chat_effort_profile
    from engine.chat.models import ChatAgentInput, ChatStreamEvent


def __getattr__(name: str) -> Any:
    module_path = _EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module_path), name)


def __dir__() -> list[str]:
    return sorted(__all__)
