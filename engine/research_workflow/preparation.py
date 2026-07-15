"""Bounded research-intake contracts and prompt assembly."""
from __future__ import annotations

import hashlib
import re
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from engine.entity_resolution import EntityResolutionStatus, EntityScope
from engine.chat.capability_router import repository_url, select_capability
from engine.utils.json_parser import extract_object
from engine.tools.contracts import CodeExecutionArguments, DatasetAnalysisArguments


class TextModel(Protocol):
    async def complete(self, prompt: str, *, max_output_tokens: int) -> str: ...


class ClarificationQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=500)
    reason: str = Field(default="", max_length=300)


class ExecutionRequirement(BaseModel):
    """Server-validated execution need; model-generated resource IDs are never accepted."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["repository", "code", "dataset", "service", "gpu"]
    required: bool = True
    resource_reference: str | None = Field(default=None, max_length=2_000)
    objectives: list[str] = Field(default_factory=list, max_length=5)
    actions: list[str] = Field(default_factory=list, max_length=8)
    profile: Literal["repository", "repository_build", "code", "data", "service", "gpu"]
    validated_arguments: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_execution_resource(self) -> "ExecutionRequirement":
        if self.kind == "repository":
            if self.resource_reference is not None:
                normalized = repository_url(self.resource_reference)
                if normalized != self.resource_reference.rstrip("/"):
                    raise ValueError("repository resources must be public GitHub repository roots")
                self.resource_reference = normalized
            if self.validated_arguments:
                raise ValueError("repository execution arguments are derived from bounded actions")
        elif self.resource_reference is not None and not re.fullmatch(
            r"inline://sha256/[a-f0-9]{64}", self.resource_reference
        ):
            raise ValueError("inline execution resources must use an opaque SHA-256 reference")
        if self.kind in {"code", "gpu"} and self.validated_arguments:
            CodeExecutionArguments.model_validate(self.validated_arguments)
        if self.kind == "dataset" and self.validated_arguments:
            DatasetAnalysisArguments.model_validate(self.validated_arguments)
        return self


class ResearchBrief(BaseModel):
    # Models sometimes attach harmless rationale/metadata keys. The brief
    # contract remains strict for consumed fields without rejecting those keys.
    model_config = ConfigDict(extra="ignore")

    refined_objective: str = Field(min_length=1, max_length=10_000)
    plan_points: list[str] = Field(min_length=4, max_length=5)
    questions: list[ClarificationQuestion] = Field(default_factory=list, max_length=4)
    must_haves: list[str] = Field(default_factory=list, max_length=12)
    deliverable: str = Field(default="Research report", max_length=500)
    entity_scope: EntityScope = Field(default_factory=EntityScope)
    assumptions: list[str] = Field(default_factory=list, max_length=12)
    execution_requirements: list[ExecutionRequirement] = Field(default_factory=list, max_length=4)

    @field_validator("plan_points", mode="before")
    @classmethod
    def concise_plan(cls, values: Any) -> list[str]:
        if not isinstance(values, list):
            raise ValueError("plan_points must be an array")
        cleaned: list[str] = []
        for value in values:
            if isinstance(value, dict):
                value = value.get("text") or value.get("point") or value.get("step") or value.get("value") or ""
            text = " ".join(str(value).split())[:220]
            if text:
                cleaned.append(text)
        cleaned = list(dict.fromkeys(cleaned))[:5]
        if not 4 <= len(cleaned) <= 5:
            raise ValueError("plan_points must contain four or five non-empty pointers")
        return cleaned

    @field_validator("questions", mode="before")
    @classmethod
    def normalize_questions(cls, values: Any) -> list[dict[str, str]]:
        if not isinstance(values, list):
            return []
        normalized: list[dict[str, str]] = []
        for index, value in enumerate(values[:4], start=1):
            if isinstance(value, ClarificationQuestion):
                value = value.model_dump(mode="json")
            if isinstance(value, str):
                value = {"text": value}
            if not isinstance(value, dict):
                continue
            text = value.get("text") or value.get("question") or value.get("prompt")
            if not text:
                continue
            normalized.append({
                "question_id": str(value.get("question_id") or value.get("id") or f"q{index}")[:80],
                "text": " ".join(str(text).split())[:500],
                "reason": " ".join(str(value.get("reason") or value.get("rationale") or "").split())[:300],
            })
        return normalized

    @field_validator("must_haves", "assumptions", mode="before")
    @classmethod
    def normalize_brief_values(cls, values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        normalized: list[str] = []
        for value in values:
            if isinstance(value, dict):
                value = value.get("text") or value.get("value") or value.get("requirement") or value.get("assumption") or ""
            text = " ".join(str(value).split())
            if text:
                normalized.append(text)
        return list(dict.fromkeys(normalized))[:12]

    @field_validator("deliverable", mode="before")
    @classmethod
    def normalize_deliverable(cls, value: Any) -> str:
        if isinstance(value, dict):
            value = value.get("text") or value.get("format") or value.get("value") or "Research report"
        return " ".join(str(value or "Research report").split())[:500]

def parse_brief(text: str) -> ResearchBrief:
    payload = extract_object(text)
    if payload is None:
        raise ValueError("research preparation model did not return a JSON object")
    return ResearchBrief.model_validate(payload)


def with_validated_execution_requirements(brief: ResearchBrief, query: str) -> ResearchBrief:
    """Derive execution requirements from the original request, not model output."""
    return brief.model_copy(update={
        "execution_requirements": validated_execution_requirements(query, brief.plan_points)
    })


def validated_execution_requirements(
    query: str, objectives: list[str] | tuple[str, ...] = ()
) -> list[ExecutionRequirement]:
    """Build the bounded, policy-selected execution contract for a request."""
    decision = select_capability(query)
    if decision.kind != "sandbox":
        return []
    lowered = query.lower()
    if decision.repository_url or any(term in lowered for term in ("repo", "repository", "codebase")):
        kind: Literal["repository", "code", "dataset", "service", "gpu"] = "repository"
        profile = "repository_build" if any(term in lowered for term in ("build", "test", "install")) else "repository"
        resource = decision.repository_url
        actions = ["clone", "resolve_commit", "inspect_files"]
        if profile == "repository_build":
            actions.extend(["install_bounded_dependencies", "run_checks"])
    elif any(term in lowered for term in ("gpu", "cuda", "pytorch", "tensorflow")):
        kind, profile, resource, actions = "gpu", "gpu", None, ["write_inputs", "execute", "verify_outputs"]
    elif any(term in lowered for term in ("service", "server", "web app", "api server")):
        kind, profile, resource, actions = "service", "service", None, ["write_inputs", "start_service", "readiness_probe"]
    elif any(term in lowered for term in ("dataset", "csv", "dataframe", "pandas", "numpy")):
        kind, profile, resource, actions = "dataset", "data", None, ["write_inputs", "execute_analysis", "verify_outputs"]
    else:
        kind, profile, resource, actions = "code", "code", None, ["write_inputs", "execute", "run_checks"]
    validated_arguments: dict[str, Any] = {}
    if kind == "dataset":
        block = _inline_fenced_block(query, preferred_languages={"csv"})
        if block is not None:
            resource = _inline_reference(block)
            validated_arguments = {
                "dataset_csv": block,
                "python_code": (
                    "import json\nimport pandas as pd\n"
                    "df = pd.read_csv('input.csv')\n"
                    "print(json.dumps({\n"
                    "  'rows': int(len(df)), 'columns': list(df.columns),\n"
                    "  'missing': {str(k): int(v) for k, v in df.isna().sum().items()},\n"
                    "  'summary': df.describe(include='all').fillna('').astype(str).to_dict(),\n"
                    "}, default=str))\n"
                ),
            }
    elif kind in {"code", "gpu"}:
        block_info = _inline_code_block(query)
        if block_info is not None:
            language, block = block_info
            resource = _inline_reference(block)
            if language in {"javascript", "js", "node", "typescript", "ts"}:
                filename, command = "main.js", ["node", "main.js"]
            else:
                filename, command = "main.py", ["python", "main.py"]
            validated_arguments = {"files": {filename: block}, "command": command}
    requirement = ExecutionRequirement(
        kind=kind,
        required=True,
        resource_reference=resource,
        objectives=list(objectives)[:5],
        actions=actions,
        profile=profile,
        validated_arguments=validated_arguments,
    )
    return [requirement]


_FENCED_BLOCK = re.compile(r"```([A-Za-z0-9_+-]*)\s*\n([\s\S]*?)```", re.MULTILINE)


def _inline_reference(content: str) -> str:
    return f"inline://sha256/{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def _inline_fenced_block(query: str, *, preferred_languages: set[str]) -> str | None:
    matches = [(language.lower(), body.strip()) for language, body in _FENCED_BLOCK.findall(query)]
    for language, body in matches:
        if language in preferred_languages and body:
            return body
    for _language, body in matches:
        if body and "," in body and "\n" in body:
            return body
    return None


def _inline_code_block(query: str) -> tuple[str, str] | None:
    for language, body in _FENCED_BLOCK.findall(query):
        if body.strip() and language.lower() not in {"csv", "json", "yaml", "yml"}:
            return language.lower(), body.strip()
    return None


def ensure_ask_question(brief: ResearchBrief) -> ResearchBrief:
    """Repair a draft that omitted questions without spending another call."""
    if brief.questions:
        return brief
    if brief.entity_scope.status == EntityResolutionStatus.AMBIGUOUS and brief.entity_scope.entities:
        mention = brief.entity_scope.entities[0].mention
        text = f"Which {mention} do you mean? Please provide a role, location, website, ticker, or full name."
        reason = "The name can refer to multiple real-world entities."
    else:
        text = "What is the single most important outcome this research should optimize for?"
        reason = "This locks the report's priority before the full research budget is spent."
    return brief.model_copy(
        update={"questions": [ClarificationQuestion(question_id="priority", text=text, reason=reason)]}
    )


def initial_brief_prompt(*, query: str, approval_mode: str) -> str:
    question_policy = (
        "Return 1-4 important clarification questions. Ask about ambiguous named entities first. "
        "Never ask a question whose answer is already present."
        if approval_mode == "ask"
        else "Return no questions. Mark unresolved named entities ambiguous so a discovery pass can resolve them."
    )
    return f"""Prepare a bounded research brief from the user's request.
Return JSON only with exactly these keys:
refined_objective (string), plan_points (array of 4-5 concise action pointers),
questions (array of objects with question_id, text, reason; maximum 4),
must_haves (array), deliverable (string), entity_scope, assumptions (array),
execution_requirements (empty array; the server derives this from the original request).
entity_scope must contain status (none|resolved|ambiguous), entities, relationship_constraints,
resolution_mode ({approval_mode}), and assumptions. Each entity contains entity_id, mention,
canonical_name, entity_type, aliases, identifiers, anchors, selected_description, confidence.
Only use aliases, identifiers, and anchors grounded in the request. Do not silently choose a
popular namesake. {question_policy}

User request:
{query}"""


def final_brief_prompt(
    *,
    query: str,
    draft: ResearchBrief,
    answers: dict[str, str],
    approval_mode: str,
    discovery_sources: list[dict[str, Any]] | None = None,
) -> str:
    evidence = discovery_sources or []
    return f"""Finalize a research brief and freeze its entity identities.
Return the same JSON contract as the draft. plan_points must contain exactly 4-5 concise pointers.
Return questions as an empty array. Preserve the user's entity, date, geography, audience, and
deliverable constraints. In ask mode, use the user's answers as authoritative. In auto mode,
select the single best contextual entity candidate even when confidence is low, record that
choice in assumptions, and set status=resolved. Never treat candidate-discovery snippets as
research evidence.

Approval mode: {approval_mode}
Original request: {query}
Draft: {draft.model_dump_json()}
Answers: {answers}
Entity discovery candidates: {evidence[:8]}"""
