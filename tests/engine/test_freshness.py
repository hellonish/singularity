from engine.chat.freshness import requests_tool_use, requires_fresh_evidence, route_chat_request


def test_current_events_language_requires_live_evidence() -> None:
    assert requires_fresh_evidence("What's going on with Anthropic and OpenAI?")
    assert requires_fresh_evidence("What is the latest OpenAI release?")


def test_stable_question_does_not_require_live_evidence() -> None:
    assert not requires_fresh_evidence("Explain the transformer architecture")
    assert not requests_tool_use("Explain the transformer architecture")


def test_explicit_retrieval_request_enters_tool_routing() -> None:
    assert requests_tool_use("Search for papers about sparse attention")


def test_relative_date_job_search_enters_fresh_retrieval() -> None:
    message = "Can you find me Job Postings in past 7 days for New Grad SWE?"

    route = route_chat_request(message)

    assert route.tool_requested is True
    assert route.needs_fresh_evidence is True
    assert route.reason == "relative_time"


def test_retry_follow_up_inherits_the_prior_live_request() -> None:
    prior = "Can you find me Job Postings in past 7 days for New Grad SWE?"

    route = route_chat_request("Can you try now?", context=f"User: {prior}\nAssistant: unavailable")

    assert route.tool_requested is True
    assert route.needs_fresh_evidence is True
    assert route.tool_query == prior
    assert route.reason == "retry_prior_live_request"
