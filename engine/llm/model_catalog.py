"""Offline datastore of known model structured-output capability.

Determining whether a model supports structured outputs (``response_format``)
otherwise costs a live provider round-trip: OpenRouter only advertises it via
the ``supported_parameters`` field of its ``/models`` catalog. That catalog is
stable for well-known models, so we curate the answer here and consult it before
falling back to network-derived detection. Groq and DeepSeek expose JSON mode as
part of their base chat contract, so their models are structured-output capable
by default and need no per-model entry.

Only the *positive-and-negative certainties* live here. A model absent from the
table returns ``None`` ("unknown"), and the caller keeps its existing live
detection. Curated entries never override a provider that has since dropped
support at runtime — they are a zero-call fast path, not an authority. Re-verify
against OpenRouter model pages and upstream provider docs when editing.
"""
from __future__ import annotations

# Substring-matched prefixes, mirroring ``_CURATED_MAX_COMPLETION_TOKENS`` so
# provider-routed variants (``:free``, ``:beta``, region suffixes) resolve to the
# same answer. Order does not matter; the first prefix hit wins.
_STRUCTURED_OUTPUT_SUPPORT: tuple[tuple[str, bool], ...] = (
    # OpenAI on OpenRouter — all advertise response_format / json_schema.
    ("openai/gpt-4o", True),
    ("openai/gpt-4o-mini", True),
    ("openai/gpt-4.1", True),
    ("openai/gpt-4.1-mini", True),
    ("openai/gpt-oss-120b", True),
    # Anthropic Claude on OpenRouter — response_format is honored.
    ("anthropic/claude-haiku-4.5", True),
    ("anthropic/claude-sonnet-4", True),
    ("anthropic/claude-3.5-sonnet", True),
    ("anthropic/claude-3.5-haiku", True),
    # Google Gemini on OpenRouter.
    ("google/gemini-2.5-pro", True),
    ("google/gemini-2.5-flash", True),
    ("google/gemini-2.0-flash", True),
    # Known-unreliable: advertises response_format but has returned non-object
    # JSON on routed research completions (see openrouter._RESEARCH_UNRELIABLE_MODELS).
    ("openai/gpt-oss-20b", False),
)

# Providers whose entire catalog supports JSON-object mode as part of the base
# chat-completions contract. No per-model lookup is ever required for these.
_STRUCTURED_OUTPUT_PROVIDERS: frozenset[str] = frozenset({"groq", "deepseek"})


def known_structured_output_support(provider: str, model_id: str) -> bool | None:
    """Return cached structured-output support, or ``None`` when unknown.

    ``None`` means "no offline answer — use live detection". A concrete bool is
    a zero-network fast path the caller may trust for a known model.
    """
    if provider in _STRUCTURED_OUTPUT_PROVIDERS:
        return True
    normalized = model_id.lower()
    for prefix, supported in _STRUCTURED_OUTPUT_SUPPORT:
        if normalized.startswith(prefix):
            return supported
    return None
