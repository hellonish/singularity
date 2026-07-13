from engine.chat.freshness import requests_tool_use, requires_fresh_evidence


def test_current_events_language_requires_live_evidence() -> None:
    assert requires_fresh_evidence("What's going on with Anthropic and OpenAI?")
    assert requires_fresh_evidence("What is the latest OpenAI release?")


def test_stable_question_does_not_require_live_evidence() -> None:
    assert not requires_fresh_evidence("Explain the transformer architecture")
    assert not requests_tool_use("Explain the transformer architecture")


def test_explicit_retrieval_request_enters_tool_routing() -> None:
    assert requests_tool_use("Search for papers about sparse attention")
