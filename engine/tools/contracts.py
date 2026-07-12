"""Validated contracts for skill-scoped trusted tool execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from engine.chat.effort import ChatEffort, get_chat_effort_profile

from .registry import TOOL_REGISTRY


class _Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchArguments(_Arguments):
    max_results: int = Field(default=10, ge=1, le=50)


class ArxivArguments(SearchArguments):
    max_age_years: float | None = Field(default=None, gt=0)


class UrlArguments(_Arguments):
    url: str = Field(min_length=8, pattern=r"^https?://")


class WebFetchArguments(UrlArguments):
    max_characters: int = Field(default=50_000, ge=1_000, le=100_000)


class BrowserRenderArguments(WebFetchArguments):
    wait_milliseconds: int = Field(default=1_000, ge=0, le=5_000)


class CalculatorArguments(_Arguments):
    precision: int = Field(default=6, ge=0, le=12)


class CurrentTimeArguments(_Arguments):
    timezone_name: str = Field(default="UTC", min_length=1, max_length=64)
    at_iso: str | None = Field(default=None, max_length=64)
    add_days: int = Field(default=0, ge=-36_500, le=36_500)
    add_hours: int = Field(default=0, ge=-876_000, le=876_000)


class RepositoryInspectionArguments(_Arguments):
    repository_url: str = Field(pattern=r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$")
    ref: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._/-]{1,200}$")
    operations: list[Literal["files", "git_summary", "tests", "static_analysis"]] = Field(
        default_factory=lambda: ["files"], min_length=1, max_length=4
    )


class DatasetAnalysisArguments(_Arguments):
    dataset_csv: str = Field(min_length=1, max_length=5_000_000)
    python_code: str = Field(min_length=1, max_length=20_000)


class TranslationArguments(_Arguments):
    source_lang: str = Field(default="auto", min_length=2, max_length=16)
    target_lang: str = Field(default="en", min_length=2, max_length=16)


TOOL_ARGUMENT_MODELS: dict[str, type[BaseModel]] = {
    "arxiv": ArxivArguments,
    "pdf_reader": UrlArguments,
    "web_fetch": WebFetchArguments,
    "browser_render": BrowserRenderArguments,
    "calculator": CalculatorArguments,
    "current_time": CurrentTimeArguments,
    "repository_inspection": RepositoryInspectionArguments,
    "dataset_analysis": DatasetAnalysisArguments,
    "translation": TranslationArguments,
    **{
        name: SearchArguments
        for name in (
            "clinicaltrials",
            "courtlistener",
            "dataset_hub",
            "github",
            "google_books",
            "pubmed",
            "sec_edgar",
            "semantic_scholar",
            "standards_fetch",
            "web_search",
            "youtube_transcript",
        )
    },
}


class ChatToolInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=128)
    skill_id: str = Field(min_length=1, max_length=128)
    tool_name: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=20_000)
    arguments: dict[str, Any] = Field(default_factory=dict)
    effort: ChatEffort = ChatEffort.MEDIUM
    timeout_seconds: int = Field(ge=1, le=420)
    profile_limits: dict[str, int] | None = None


@dataclass(frozen=True)
class ValidatedChatToolInvocation:
    run_id: str
    skill_id: str
    tool_name: str
    query: str
    arguments: dict[str, Any]
    effort: ChatEffort
    timeout_seconds: int

    def payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "skill_id": self.skill_id,
            "tool_name": self.tool_name,
            "query": self.query,
            "arguments": self.arguments,
            "effort": self.effort,
            "timeout_seconds": self.timeout_seconds,
            "profile_limits": {
                "max_agent_tool_steps": get_chat_effort_profile(self.effort).max_agent_tool_steps,
                "max_calls_per_tool_type": get_chat_effort_profile(self.effort).max_calls_per_tool_type,
                "timeout_seconds": self.timeout_seconds,
            },
        }


def validate_chat_tool_invocation(invocation: ChatToolInvocation) -> ValidatedChatToolInvocation:
    from engine.skills import SKILL_REGISTRY

    skill = SKILL_REGISTRY.get(invocation.skill_id)
    TOOL_REGISTRY.descriptor(invocation.tool_name)
    if invocation.tool_name not in skill.config.tools:
        raise ValueError(f"tool {invocation.tool_name!r} is not allowed by skill {invocation.skill_id!r}")
    try:
        arguments_model = TOOL_ARGUMENT_MODELS[invocation.tool_name]
    except KeyError as exc:
        raise ValueError(f"tool {invocation.tool_name!r} has no chat execution contract") from exc
    arguments = arguments_model.model_validate(invocation.arguments).model_dump(exclude_none=True)
    profile = get_chat_effort_profile(invocation.effort)
    expected_limits = {
        "max_agent_tool_steps": profile.max_agent_tool_steps,
        "max_calls_per_tool_type": profile.max_calls_per_tool_type,
        "timeout_seconds": profile.timeout_seconds,
    }
    if invocation.timeout_seconds != profile.timeout_seconds:
        raise ValueError("timeout_seconds must match the selected chat effort profile")
    if invocation.profile_limits is not None and invocation.profile_limits != expected_limits:
        raise ValueError("profile_limits must match the selected chat effort profile")
    return ValidatedChatToolInvocation(
        run_id=invocation.run_id,
        skill_id=invocation.skill_id,
        tool_name=invocation.tool_name,
        query=invocation.query,
        arguments=arguments,
        effort=invocation.effort,
        timeout_seconds=invocation.timeout_seconds,
    )


def tool_schema_for_skill(skill_id: str) -> list[dict[str, Any]]:
    """OpenAI-compatible tool schemas limited to one registered skill."""
    from engine.skills import SKILL_REGISTRY

    skill = SKILL_REGISTRY.get(skill_id)
    schemas = []
    for name in skill.config.tools:
        model = TOOL_ARGUMENT_MODELS.get(name)
        if model is None:
            continue
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": TOOL_REGISTRY.descriptor(name).description,
                    "parameters": model.model_json_schema(),
                },
            }
        )
    return schemas


def chat_planner_tool_schemas(
    *, allowed_execution_kinds: tuple[str, ...] = ("trusted_function",)
) -> tuple[list[dict[str, Any]], dict[str, tuple[str, str]]]:
    """Return unique Groq function schemas and their skill/tool bindings."""
    from engine.skills import SKILL_REGISTRY

    schemas: list[dict[str, Any]] = []
    bindings: dict[str, tuple[str, str]] = {}
    for skill in SKILL_REGISTRY.definitions():
        for tool_name in skill.config.tools:
            if TOOL_REGISTRY.descriptor(tool_name).execution_kind not in allowed_execution_kinds:
                continue
            arguments_model = TOOL_ARGUMENT_MODELS.get(tool_name)
            if arguments_model is None:
                continue
            function_name = f"{skill.id}__{tool_name}"
            bindings[function_name] = (skill.id, tool_name)
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "description": TOOL_REGISTRY.descriptor(tool_name).description,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "minLength": 1},
                                "arguments": arguments_model.model_json_schema(),
                            },
                            "required": ["query", "arguments"],
                            "additionalProperties": False,
                        },
                    },
                }
            )
    return schemas, bindings
