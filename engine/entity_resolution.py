"""Shared entity identity contracts and fail-closed source admission.

The resolver deliberately prefers precision to recall.  A search result that
mentions the right surface name but none of the user's disambiguating anchors
is not admitted as evidence for that entity.
"""
from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntityResolutionStatus(StrEnum):
    NONE = "none"
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"


def _string_list(values: Any, *, keys: tuple[str, ...] = ("value", "name", "id", "text")) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for item in values:
        if isinstance(item, dict):
            item = next((item.get(key) for key in keys if item.get(key)), "")
        if not isinstance(item, (str, int, float)):
            continue
        text = " ".join(str(item).split())
        if text:
            normalized.append(text)
    return list(dict.fromkeys(normalized))


class EntityRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str = Field(min_length=1, max_length=80)
    mention: str = Field(min_length=1, max_length=240)
    canonical_name: str = Field(min_length=1, max_length=240)
    entity_type: str = Field(default="unknown", max_length=80)
    aliases: list[str] = Field(default_factory=list, max_length=12)
    identifiers: list[str] = Field(default_factory=list, max_length=12)
    anchors: list[str] = Field(default_factory=list, max_length=12)
    selected_description: str = Field(default="", max_length=600)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("aliases", "identifiers", "anchors", mode="before")
    @classmethod
    def normalize_values(cls, values: Any) -> list[str]:
        """Accept compact strings or provider-emitted typed discriminator objects."""
        return _string_list(values)


class EntityScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EntityResolutionStatus = EntityResolutionStatus.NONE
    entities: list[EntityRef] = Field(default_factory=list, max_length=12)
    relationship_constraints: list[str] = Field(default_factory=list, max_length=12)
    resolution_mode: str = Field(default="ask", pattern="^(ask|auto|chat)$")
    assumptions: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("relationship_constraints", "assumptions", mode="before")
    @classmethod
    def normalize_scope_values(cls, values: Any) -> list[str]:
        return _string_list(values, keys=("value", "text", "constraint", "assumption", "name"))

    @property
    def resolved(self) -> bool:
        return self.status in {EntityResolutionStatus.NONE, EntityResolutionStatus.RESOLVED}


class SourceEntityDecision(StrEnum):
    ALIGNED = "aligned"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"


class SourceEntityVerdict(BaseModel):
    decision: SourceEntityDecision
    matched_entity_ids: list[str] = Field(default_factory=list)
    reason: str


_TOKEN = re.compile(r"[a-z0-9]+")
_CAPITALIZED = re.compile(r"\b(?:[A-Z][A-Za-z0-9&.'-]*)(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,3}\b")
_QUOTED = re.compile(r"[\"']([^\"']{2,120})[\"']")
_DOMAIN = re.compile(r"\b(?:https?://)?(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)+)\b", re.IGNORECASE)
_TICKER = re.compile(r"(?<!\w)\$[A-Z]{1,6}\b")
_GENERIC_FIRST = {
    "Can", "Could", "Find", "Give", "How", "Latest", "List", "Look", "Please",
    "Research", "Search", "Show", "Tell", "The", "What", "When", "Where", "Which", "Who", "Why",
}
_ROUTING_WORDS = {
    "latest", "current", "today", "recent", "news", "search", "find", "look", "research",
    "about", "for", "on", "the", "a", "an", "please", "tell", "show", "me", "what", "who",
    "and", "with", "going", "can", "you", "past", "days", "in", "of", "to", "at", "com",
}
_GENERIC_MENTION_TOKENS = {
    "job", "jobs", "posting", "postings", "listing", "listings", "role", "roles",
    "opening", "openings", "new", "grad", "graduate", "swe", "engineer", "engineering",
}


def normalize(text: str) -> str:
    return " ".join(_TOKEN.findall(text.lower()))


def _contains(haystack: str, needle: str) -> bool:
    normalized = normalize(needle)
    return bool(normalized) and f" {normalized} " in f" {haystack} "


def classify_source(source: dict[str, Any], scope: EntityScope) -> SourceEntityVerdict:
    """Classify one candidate without spending a model call."""
    if scope.status == EntityResolutionStatus.NONE or not scope.entities:
        return SourceEntityVerdict(decision=SourceEntityDecision.ALIGNED, reason="entity_free_request")
    if scope.status == EntityResolutionStatus.AMBIGUOUS:
        return SourceEntityVerdict(decision=SourceEntityDecision.REJECTED, reason="entity_scope_ambiguous")

    corpus = normalize(" ".join(str(source.get(key, "")) for key in ("title", "url", "snippet", "content")))
    matched: list[str] = []
    uncertain = False
    for entity in scope.entities:
        names = [entity.canonical_name, entity.mention, *entity.aliases]
        name_match = any(_contains(corpus, value) for value in names)
        discriminators = [*entity.identifiers, *entity.anchors]
        discriminator_match = not discriminators or any(
            _contains(corpus, value) for value in discriminators
        )
        if name_match and discriminator_match:
            matched.append(entity.entity_id)
            continue
        if name_match:
            uncertain = True
            continue
        # A source may legitimately cover only one entity in a multi-entity
        # investigation. Missing mentions are neutral; a surface-name match
        # without its frozen discriminator is not.
        continue
    if uncertain:
        return SourceEntityVerdict(
            decision=SourceEntityDecision.UNCERTAIN,
            matched_entity_ids=matched,
            reason="name_without_disambiguating_anchor",
        )
    if matched:
        return SourceEntityVerdict(
            decision=SourceEntityDecision.ALIGNED,
            matched_entity_ids=matched,
            reason="identity_and_anchor_match",
        )
    return SourceEntityVerdict(
        decision=SourceEntityDecision.REJECTED,
        reason="no_frozen_identity_match",
    )


def scope_search_query(query: str, scope: EntityScope) -> str:
    """Append only the frozen, user-approved identity discriminators."""
    if scope.status == EntityResolutionStatus.NONE or not scope.entities:
        return query
    constraints: list[str] = []
    for entity in scope.entities:
        parts = [entity.canonical_name, entity.entity_type, *entity.identifiers, *entity.anchors]
        constraints.append(" ".join(dict.fromkeys(part for part in parts if part and part != "unknown")))
    suffix = " ; ".join(item for item in constraints if item)
    return f"{query} [target entity: {suffix}]" if suffix else query


def lightweight_chat_scope(message: str, *, context: str = "") -> EntityScope:
    """Conservative zero-call resolver for latency-sensitive Chat retrieval.

    It never invents aliases.  Bare proper names are treated as ambiguous;
    names accompanied by prompt-grounded context or a stable identifier are
    frozen using their exact surface form.
    """
    combined = f"{context[-2_000:]}\n{message}"
    mentions = [match.group(1).strip() for match in _QUOTED.finditer(message)]
    for match in _CAPITALIZED.finditer(message):
        words = match.group(0).strip().split()
        while words and words[0] in _GENERIC_FIRST:
            words.pop(0)
        if words:
            mentions.append(" ".join(words))
    mentions = [mention for mention in mentions if mention not in _GENERIC_FIRST]
    mentions = [
        mention for mention in mentions
        if not set(_TOKEN.findall(mention.lower())).issubset(_GENERIC_MENTION_TOKENS)
    ]
    mentions = list(dict.fromkeys(mentions))[:4]
    identifiers = [match.group(1) for match in _DOMAIN.finditer(combined)]
    identifiers.extend(match.group(0) for match in _TICKER.finditer(combined))
    if not mentions and not identifiers:
        return EntityScope(status=EntityResolutionStatus.NONE, resolution_mode="chat")

    message_tokens = [token for token in _TOKEN.findall(message.lower()) if token not in _ROUTING_WORDS]
    mention_tokens = {token for mention in mentions for token in _TOKEN.findall(mention.lower())}
    anchors = [token for token in message_tokens if token not in mention_tokens and len(token) > 2]
    anchors = list(dict.fromkeys(anchors))[:6]
    ambiguous = not identifiers and not anchors and len(mentions) <= 1
    entities = [
        EntityRef(
            entity_id=f"chat_{index + 1}",
            mention=mention,
            canonical_name=mention,
            identifiers=identifiers if index == 0 else [],
            anchors=anchors,
            confidence=0.85 if identifiers else 0.65 if anchors else 0.0,
        )
        for index, mention in enumerate(mentions or identifiers[:1])
    ]
    return EntityScope(
        status=EntityResolutionStatus.AMBIGUOUS if ambiguous else EntityResolutionStatus.RESOLVED,
        entities=entities,
        resolution_mode="chat",
    )


def clarification_for_scope(scope: EntityScope) -> str:
    mention = scope.entities[0].mention if scope.entities else "that entity"
    return (
        f"Which {mention} do you mean? Please add one identifying detail—such as its "
        "industry or role, location, official website, ticker, or full legal name—before I search."
    )
