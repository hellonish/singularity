"""Deterministic heuristics for requests that require live public evidence.

This runs before the answer model. A positive match makes retrieval
*mandatory* (the runtime fails closed if no evidence is collected) and seeds
an immediate discovery burst. A miss is advisory, not a gate: the runtime
still gives the model planner a chance to decide, with the route passed along
as a hint, so unanticipated phrasings degrade to model judgment instead of
silently skipping retrieval.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


_FRESHNESS_PHRASES = (
    "latest", "current", "today", "yesterday", "recent", "right now",
    "what's going on", "whats going on", "what is going on", "news",
    "price", "weather", "schedule", "release", "version", "ceo",
    "president", "open roles", "announced",
)

_EXPLICIT_TOOL_PHRASES = (
    "search for", "look up", "find sources", "research", "use the web",
    "calculate", "arxiv", "pubmed", "github", "sec filing", "court case",
    "clinical trial", "paper", "dataset", "youtube transcript", "pdf",
    "write code", "run code", "execute code", "run tests", "debug", "implement",
)

_RELATIVE_TIME = re.compile(
    r"\b(?:past|last)\s+\d+\s+(?:minutes?|hours?|days?|weeks?|months?|years?)\b"
    r"|\b(?:this|next|previous|past|last)\s+(?:week|month|year|quarter|weekend)\b"
    r"|\b(?:since|before|after)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
_DISCOVERY_VERB = re.compile(
    r"\b(?:search(?:ing)?|find|show|list|locate|browse|track|get)\b", re.IGNORECASE
)
_LIVE_JOB_RESOURCE = re.compile(
    r"\b(?:job postings?|job listings?|open roles?|openings|vacancies|career (?:pages?|roles?)|"
    r"new[- ]grad|entry[- ]level|hiring)\b",
    re.IGNORECASE,
)
_RETRY_FOLLOW_UP = re.compile(
    r"^\s*(?:can you )?(?:try (?:again|now)|retry|do (?:that|it)|go ahead|yes(?: please)?|"
    r"please do|continue)\s*[?.!]*\s*$",
    re.IGNORECASE,
)
_USER_TURN = re.compile(
    r"(?ims)^(?:user):\s*(.+?)(?=^(?:user|assistant):|\Z)"
)


@dataclass(frozen=True)
class ChatRoute:
    """The routing decision consumed by the bounded chat runtime."""

    tool_requested: bool
    needs_fresh_evidence: bool
    tool_query: str
    answer_message: str
    reason: str | None = None


def route_chat_request(message: str, *, context: str = "") -> ChatRoute:
    """Classify a turn and resolve terse retries to the preceding live request.

    Relative dates are parsed structurally rather than through an ever-growing
    phrase list.  Job discovery is also live by nature when phrased as a user
    request ("find me new-grad roles"), even if it omits an explicit date.
    """
    normalized = " ".join(message.lower().split())
    has_relative_time = bool(_RELATIVE_TIME.search(normalized))
    has_fresh_phrase = any(phrase in normalized for phrase in _FRESHNESS_PHRASES)
    has_explicit_tool_phrase = any(phrase in normalized for phrase in _EXPLICIT_TOOL_PHRASES)
    is_job_discovery = bool(_LIVE_JOB_RESOURCE.search(normalized)) and bool(
        _DISCOVERY_VERB.search(normalized) or has_relative_time
    )

    if has_relative_time or has_fresh_phrase:
        return ChatRoute(True, True, message, message, "relative_time" if has_relative_time else "freshness_phrase")
    if is_job_discovery:
        return ChatRoute(True, True, message, message, "live_job_discovery")
    if has_explicit_tool_phrase:
        return ChatRoute(True, False, message, message, "explicit_tool_request")

    if _RETRY_FOLLOW_UP.fullmatch(message):
        prior = _latest_live_user_request(context)
        if prior is not None:
            return ChatRoute(
                True,
                True,
                prior,
                (
                    "The user asked you to retry the following live request. Answer that request "
                    "using the supplied evidence.\n\n"
                    f"Request: {prior}\nFollow-up: {message}"
                ),
                "retry_prior_live_request",
            )

    return ChatRoute(False, False, message, message)


def _latest_live_user_request(context: str) -> str | None:
    """Return the latest prior user turn that itself required fresh evidence."""
    turns = [" ".join(match.group(1).split()) for match in _USER_TURN.finditer(context)]
    for turn in reversed(turns):
        route = route_chat_request(turn)
        if route.needs_fresh_evidence:
            return turn
    return None


def requires_fresh_evidence(message: str, *, context: str = "") -> bool:
    return route_chat_request(message, context=context).needs_fresh_evidence


def requests_tool_use(message: str, *, context: str = "") -> bool:
    """Avoid LLM tool planning for ordinary conversational turns."""
    return route_chat_request(message, context=context).tool_requested
