"""Bounded research-intake contracts and prompt assembly."""
from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from engine.entity_resolution import EntityResolutionStatus, EntityScope
from engine.utils.json_parser import extract_object


class TextModel(Protocol):
    async def complete(self, prompt: str, *, max_output_tokens: int) -> str: ...


class ClarificationQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=500)
    reason: str = Field(default="", max_length=300)


class ResearchBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refined_objective: str = Field(min_length=1, max_length=10_000)
    plan_points: list[str] = Field(min_length=4, max_length=5)
    questions: list[ClarificationQuestion] = Field(default_factory=list, max_length=4)
    must_haves: list[str] = Field(default_factory=list, max_length=12)
    deliverable: str = Field(default="Research report", max_length=500)
    entity_scope: EntityScope = Field(default_factory=EntityScope)
    assumptions: list[str] = Field(default_factory=list, max_length=12)

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
        if not 4 <= len(cleaned) <= 5:
            raise ValueError("plan_points must contain four or five non-empty pointers")
        return cleaned

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
        return list(dict.fromkeys(normalized))

def parse_brief(text: str) -> ResearchBrief:
    payload = extract_object(text)
    if payload is None:
        raise ValueError("research preparation model did not return a JSON object")
    return ResearchBrief.model_validate(payload)


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
must_haves (array), deliverable (string), entity_scope, assumptions (array).
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
