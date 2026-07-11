"""Strict JSON-schema contracts for structured LLM responses."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

STRICT_STRUCTURED_OUTPUT_MODELS = frozenset(
    {
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
    }
)


class StructuredOutputError(ValueError):
    """The supplied schema or returned structured value is invalid."""


@dataclass(frozen=True)
class StructuredOutputSpec:
    """Immutable, strict response-format contract for one provider call."""

    name: str
    schema_json: str

    @classmethod
    def create(cls, *, name: str, schema: dict[str, Any]) -> "StructuredOutputSpec":
        if not name or len(name) > 64:
            raise StructuredOutputError("Structured-output schema name must be 1-64 characters")
        try:
            schema_json = json.dumps(schema, separators=(",", ":"), sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise StructuredOutputError("Structured-output schema must be JSON serializable") from exc
        if len(schema_json) > 32_768:
            raise StructuredOutputError("Structured-output schema is too large")
        try:
            parsed_schema = json.loads(schema_json)
            Draft202012Validator.check_schema(parsed_schema)
        except Exception as exc:
            raise StructuredOutputError("Structured-output schema is not valid JSON Schema") from exc
        _validate_strict_schema(parsed_schema)
        return cls(name=name, schema_json=schema_json)

    @property
    def schema(self) -> dict[str, Any]:
        return json.loads(self.schema_json)

    def groq_response_format(self) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": self.name,
                "strict": True,
                "schema": self.schema,
            },
        }

    def parse_and_validate(self, content: str) -> Any:
        try:
            value = json.loads(content)
        except json.JSONDecodeError as exc:
            raise StructuredOutputError("Provider returned malformed JSON") from exc
        try:
            Draft202012Validator(self.schema).validate(value)
        except ValidationError as exc:
            raise StructuredOutputError("Provider output does not match the requested schema") from exc
        return value


def _validate_strict_schema(schema: dict[str, Any]) -> None:
    """Reject schemas Groq strict mode cannot guarantee before calling Groq."""

    if schema.get("type") != "object":
        raise StructuredOutputError("Strict structured-output schemas must have an object root")
    _validate_node(schema, path="$", seen=set())


def _validate_node(node: Any, *, path: str, seen: set[int]) -> None:
    if not isinstance(node, dict):
        return
    marker = id(node)
    if marker in seen:
        return
    seen.add(marker)

    if node.get("type") == "object":
        properties = node.get("properties", {})
        if not isinstance(properties, dict):
            raise StructuredOutputError(f"{path}.properties must be an object")
        if set(node.get("required", [])) != set(properties):
            raise StructuredOutputError(f"{path} must require every declared property in strict mode")
        if node.get("additionalProperties") is not False:
            raise StructuredOutputError(f"{path} must set additionalProperties to false in strict mode")
        for property_name, property_schema in properties.items():
            _validate_node(property_schema, path=f"{path}.properties.{property_name}", seen=seen)

    if "items" in node:
        _validate_node(node["items"], path=f"{path}.items", seen=seen)
    for keyword in ("allOf", "anyOf", "oneOf"):
        for index, sub_schema in enumerate(node.get(keyword, [])):
            _validate_node(sub_schema, path=f"{path}.{keyword}[{index}]", seen=seen)
    for definition_name, sub_schema in node.get("$defs", {}).items():
        _validate_node(sub_schema, path=f"{path}.$defs.{definition_name}", seen=seen)
