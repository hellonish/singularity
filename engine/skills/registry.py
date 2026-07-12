"""Discovery and validation for file-backed research skills."""
from __future__ import annotations

import importlib
from pathlib import Path

import yaml
from pydantic import BaseModel

from engine.tools import TOOL_REGISTRY

from .models import SkillConfig, SkillDefinition


class SkillRegistry:
    def __init__(self, definitions: dict[str, SkillDefinition]) -> None:
        self._definitions = definitions

    @classmethod
    def discover(cls, root: Path | None = None) -> "SkillRegistry":
        root = root or Path(__file__).parent
        definitions: dict[str, SkillDefinition] = {}

        for config_path in sorted(root.glob("*/config.yaml")):
            skill_root = config_path.parent
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config = SkillConfig.model_validate(raw)
            if config.id != skill_root.name:
                raise ValueError(
                    f"Skill config id {config.id!r} does not match directory {skill_root.name!r}"
                )
            if config.id in definitions:
                raise ValueError(f"Duplicate skill id: {config.id}")

            instructions_path = skill_root / config.instructions
            schemas_path = skill_root / config.schemas
            if not instructions_path.is_file() or not instructions_path.read_text(encoding="utf-8").strip():
                raise ValueError(f"Skill {config.id} has no usable instructions")
            if not schemas_path.is_file():
                raise ValueError(f"Skill {config.id} has no schemas module")

            for tool_name in config.tools:
                TOOL_REGISTRY.descriptor(tool_name)
                TOOL_REGISTRY.bind_skill(config.id, tool_name)

            schema_module = importlib.import_module(f"engine.skills.{config.id}.schemas")
            input_model = getattr(schema_module, "SkillInput", None)
            output_model = getattr(schema_module, "SkillOutput", None)
            if not _is_model(input_model) or not _is_model(output_model):
                raise TypeError(
                    f"engine.skills.{config.id}.schemas must export Pydantic "
                    "SkillInput and SkillOutput models"
                )

            definitions[config.id] = SkillDefinition(
                config=config,
                root=skill_root,
                instructions=instructions_path.read_text(encoding="utf-8").strip(),
                input_model=input_model,
                output_model=output_model,
            )

        return cls(definitions)

    def get(self, skill_id: str) -> SkillDefinition:
        try:
            return self._definitions[skill_id]
        except KeyError as exc:
            raise KeyError(f"Unknown skill: {skill_id}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._definitions))

    def definitions(self) -> tuple[SkillDefinition, ...]:
        return tuple(self._definitions[name] for name in self.names())


def _is_model(value: object) -> bool:
    return isinstance(value, type) and issubclass(value, BaseModel)


SKILL_REGISTRY = SkillRegistry.discover()

