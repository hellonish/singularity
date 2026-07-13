"""Deterministic routing for requests that require live public evidence."""
from __future__ import annotations


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
)


def requires_fresh_evidence(message: str) -> bool:
    normalized = " ".join(message.lower().split())
    return any(phrase in normalized for phrase in _FRESHNESS_PHRASES)


def requests_tool_use(message: str) -> bool:
    """Avoid LLM tool planning for ordinary conversational turns."""
    normalized = " ".join(message.lower().split())
    return requires_fresh_evidence(normalized) or any(
        phrase in normalized for phrase in _EXPLICIT_TOOL_PHRASES
    )
