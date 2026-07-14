from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from engine.llm import resolve_request_config
from engine.llm.structured import StructuredOutputError, StructuredOutputSpec


def test_model_selection_precedence_and_request_immutability() -> None:
    config = resolve_request_config(
        provider="groq",
        credential_id="cred_1",
        request_model_id=None,
        conversation_model_id="chat-model",
        credential_default_model_id="default-model",
        application_fallback_model_id="fallback-model",
    )
    assert config.model_id == "chat-model"
    with pytest.raises(FrozenInstanceError):
        config.model_id = "other"  # type: ignore[misc]


def test_strict_schema_rejects_optional_or_extra_properties() -> None:
    invalid_schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": [],
        "additionalProperties": True,
    }
    with pytest.raises(StructuredOutputError):
        StructuredOutputSpec.create(name="answer", schema=invalid_schema)


def test_strict_schema_validates_provider_output() -> None:
    spec = StructuredOutputSpec.create(
        name="answer",
        schema={
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        },
    )
    assert spec.parse_and_validate('{"answer":"ok"}') == {"answer": "ok"}
    with pytest.raises(StructuredOutputError):
        spec.parse_and_validate('{"answer": 1}')


def test_json_object_mode_accepts_any_valid_json_object() -> None:
    spec = StructuredOutputSpec.json_object()

    assert spec.groq_response_format() == {"type": "json_object"}
    assert spec.parse_and_validate('{"answer":"yes"}') == {"answer": "yes"}
    with pytest.raises(StructuredOutputError, match="not an object"):
        spec.parse_and_validate('["not", "an object"]')


def test_parse_recovers_json_wrapped_in_fences_or_prose() -> None:
    spec = StructuredOutputSpec.json_object()

    assert spec.parse_and_validate('```json\n{"answer":"yes"}\n```') == {"answer": "yes"}
    assert spec.parse_and_validate('Here you go:\n{"answer":"yes"}\nHope this helps!') == {"answer": "yes"}
    with pytest.raises(StructuredOutputError):
        spec.parse_and_validate('{"answer": "truncat')


def test_schema_validation_still_applies_to_recovered_json() -> None:
    spec = StructuredOutputSpec.create(
        name="answer",
        schema={
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        },
    )
    assert spec.parse_and_validate('```json\n{"answer":"ok"}\n```') == {"answer": "ok"}
    with pytest.raises(StructuredOutputError):
        spec.parse_and_validate('```json\n{"answer": 1}\n```')
