"""Declarative registry for trusted research tools.

Skills are intentionally represented by strings instead of imported classes.
That lets skill packages be introduced independently and lets one skill use
many tools without creating a circular tools <-> skills dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .base import ExecutionKind, ToolBase


@dataclass(frozen=True)
class ToolDescriptor:
    """Metadata needed by policy and a later Modal Function dispatcher."""

    name: str
    description: str
    tool_class: type[ToolBase]
    skill_ids: tuple[str, ...]
    execution_kind: ExecutionKind


class ToolRegistry:
    """Registry of trusted operations and their optional skill bindings."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDescriptor] = {}
        self._skill_bindings: dict[str, set[str]] = {}

    def register(self, tool_class: type[ToolBase]) -> None:
        name = tool_class.name
        if not name or name == "base":
            raise ValueError("Registered tools must define a non-base name")
        existing = self._tools.get(name)
        if existing and existing.tool_class is tool_class:
            return
        if existing:
            raise ValueError(f"Tool already registered: {name}")

        descriptor = ToolDescriptor(
            name=name,
            description=tool_class.description,
            tool_class=tool_class,
            skill_ids=tool_class.skill_ids,
            execution_kind=tool_class.execution_kind,
        )
        self._tools[name] = descriptor
        for skill_id in descriptor.skill_ids:
            self.bind_skill(skill_id, name)

    def bind_skill(self, skill_id: str, tool_name: str) -> None:
        """Associate a future skill identifier with a registered tool.

        Binding is additive so a skill can expose several tools, and a tool can
        be reused by several skills.  Skill definitions do not need to exist
        when bindings are declared.
        """
        if not skill_id:
            raise ValueError("skill_id must not be empty")
        if tool_name not in self._tools:
            raise KeyError(f"Unknown tool: {tool_name}")
        self._skill_bindings.setdefault(skill_id, set()).add(tool_name)

    def create(self, tool_name: str) -> ToolBase:
        """Create one trusted tool by its stable operation name."""
        try:
            return self._tools[tool_name].tool_class()
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {tool_name}") from exc

    def descriptor(self, tool_name: str) -> ToolDescriptor:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {tool_name}") from exc

    def for_skill(self, skill_id: str) -> tuple[ToolDescriptor, ...]:
        """Return the trusted tools available to a declared future skill."""
        return tuple(
            self._tools[name]
            for name in sorted(self._skill_bindings.get(skill_id, ()))
        )

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def descriptors(self) -> Iterable[ToolDescriptor]:
        return (self._tools[name] for name in self.names())


TOOL_REGISTRY = ToolRegistry()
