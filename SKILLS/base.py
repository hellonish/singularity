"""SkillBase — abstract base class for all skills.

Auto-registration:
    Any class that subclasses SkillBase and declares a ``name`` class variable
    (directly in ``__dict__``, not inherited) is automatically entered into
    ``_SKILL_REGISTRY`` when its module is imported.  ``skills/registry.py``
    consumes this dict to build the public ``SKILL_REGISTRY`` of instances.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from models import ExecutionContext, NodeStatus, PlanNode

# Internal class registry populated by __init_subclass__.
# Keys are skill names; values are the concrete SkillBase subclasses.
_SKILL_REGISTRY: dict[str, type[SkillBase]] = {}


class SkillBase:
    """Abstract base for all skills across all three tiers.

    Subclasses must set ``name`` as a class-level string and implement ``run``.
    Setting ``name`` directly on the subclass (not inheriting a parent value)
    automatically registers the class in ``_SKILL_REGISTRY``.
    """

    name: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Only register classes that explicitly declare `name` on themselves.
        skill_name = cls.__dict__.get("name", "")
        if skill_name:
            _SKILL_REGISTRY[skill_name] = cls

    async def run(
        self,
        node: "PlanNode",
        ctx: "ExecutionContext",
        client: Any,
        registry: "dict[str, SkillBase]",
    ) -> "tuple[Any, NodeStatus, float]":
        """Execute the skill for a single plan node.

        Args:
            node: The plan node this skill is fulfilling.
            ctx:  The shared ``ExecutionContext`` for the current run.
            client: The LLM client instance.
            registry: The full ``SKILL_REGISTRY`` (for skills that delegate).

        Returns:
            A ``(result_dict, NodeStatus, confidence_float)`` triple.
        """
        raise NotImplementedError
