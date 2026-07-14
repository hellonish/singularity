from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from engine.llm.groq import GroqModel, GroqProviderError, LLMCompletion
from engine.chat.models import ChatStreamEvent
from tests.sse.helpers import parse_sse


class _FakeProvider:
    """Deterministic stand-in for a BYOK provider (no network)."""

    def __init__(self, deltas: list[str]) -> None:
        self._deltas = deltas

    async def retrieve_model(self, *, api_key: str, model_id: str) -> GroqModel:
        return GroqModel(id=model_id, context_window=8_192, max_completion_tokens=1_024, active=True)

    async def stream_chat(self, *, api_key: str, config, messages):
        for delta in self._deltas:
            yield delta


class _TitledProvider(_FakeProvider):
    """Fake provider that also answers the one-shot title completion."""

    async def complete(self, *, api_key: str, config, message: str, end_user_id: str, structured_output=None):
        return LLMCompletion(content='"Diffusion Transformer Basics."', input_tokens=None, output_tokens=None)


class _FailingProvider(_FakeProvider):
    async def stream_chat(self, *, api_key: str, config, messages):
        raise GroqProviderError(code="provider_rate_limited", message="slow down", retryable=True)
        yield  # pragma: no cover - marks this an async generator


def _make_chat_with_credential(client: TestClient, headers: dict[str, str]) -> str:
    credential = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": "gsk_test_not_a_real_key", "default_model_id": "openai/gpt-oss-20b"},
        headers=headers,
    )
    assert credential.status_code == 201, credential.text
    chat = client.post(
        "/chats",
        json={"title": "SSE chat", "provider_credential_id": credential.json()["id"]},
        headers=headers,
    )
    assert chat.status_code == 201, chat.text
    return chat.json()["id"]


def test_chat_stream_emits_real_engine_events_and_persists_the_reply(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Pin tools off: this test covers the pure conversational stream shape,
    # and .env (loaded by conftest) may enable Modal for the whole run.
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "0")
    chat_id = _make_chat_with_credential(client, current_user)
    provider = _FakeProvider(["Diffusion ", "transformers ", "explained."])
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: provider)

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "Explain diffusion transformers"},
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        events = parse_sse(response.read().decode())

    kinds = [event["event"] for event in events]
    assert kinds[0] == "message.accepted"
    assert kinds[-1] == "message.completed"
    assert kinds.count("message.delta") == 3
    deltas = [event["data"]["delta"] for event in events if event["event"] == "message.delta"]
    assert "".join(deltas) == events[-1]["data"]["content"] == "Diffusion transformers explained."
    assert all(event["id"] for event in events)

    # Both the user turn and the streamed assistant reply are persisted.
    persisted = client.get(f"/chats/{chat_id}/messages", headers=current_user)
    assert persisted.status_code == 200
    roles = [(m["role"], m["content"]) for m in persisted.json()]
    assert roles == [
        ("user", "Explain diffusion transformers"),
        ("assistant", "Diffusion transformers explained."),
    ]


def test_hosted_chat_stream_forwards_shared_runtime_progress(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chat_id = _make_chat_with_credential(client, current_user)

    class Runtime:
        def __init__(self, *, provider):
            pass

        async def stream(self, request, **kwargs):
            yield ChatStreamEvent(
                type="progress",
                model_id="model",
                progress_kind="agent_budget",
                message="selected 4 of 4 agent steps",
            )
            yield ChatStreamEvent(type="started", model_id="model")
            yield ChatStreamEvent(type="delta", model_id="model", delta="grounded")
            yield ChatStreamEvent(type="completed", model_id="model", content="grounded")

    monkeypatch.setattr("api.services.chat_stream.ChatRuntime", Runtime)
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: _FakeProvider([]))

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "Find current sources"},
        headers=current_user,
    ) as response:
        events = parse_sse(response.read().decode())

    assert [event["event"] for event in events][:2] == ["message.progress", "message.accepted"]
    assert events[0]["data"]["kind"] == "agent_budget"


def _make_untitled_chat_with_credential(client: TestClient, headers: dict[str, str]) -> str:
    credential = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": "gsk_test_not_a_real_key", "default_model_id": "openai/gpt-oss-20b"},
        headers=headers,
    )
    assert credential.status_code == 201, credential.text
    chat = client.post(
        "/chats",
        json={"provider_credential_id": credential.json()["id"]},
        headers=headers,
    )
    assert chat.status_code == 201, chat.text
    assert chat.json()["title"] is None
    return chat.json()["id"]


def test_first_turn_of_untitled_chat_generates_and_persists_a_title(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chat_id = _make_untitled_chat_with_credential(client, current_user)
    provider = _TitledProvider(["Diffusion ", "transformers ", "explained."])
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: provider)

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "Explain diffusion transformers"},
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        events = parse_sse(response.read().decode())

    kinds = [event["event"] for event in events]
    assert kinds[-2] == "message.completed"
    assert kinds[-1] == "chat.title"
    # Quotes and trailing punctuation from the model reply are stripped.
    assert events[-1]["data"] == {"chat_id": chat_id, "title": "Diffusion Transformer Basics"}

    persisted = client.get(f"/chats/{chat_id}", headers=current_user)
    assert persisted.json()["title"] == "Diffusion Transformer Basics"


def test_title_generation_failure_falls_back_to_the_user_message(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chat_id = _make_untitled_chat_with_credential(client, current_user)
    # _FakeProvider has no complete(): title generation fails and falls back.
    provider = _FakeProvider(["pong"])
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: provider)

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "Explain diffusion transformers"},
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        events = parse_sse(response.read().decode())

    assert events[-1]["event"] == "chat.title"
    assert events[-1]["data"]["title"] == "Explain diffusion transformers"

    persisted = client.get(f"/chats/{chat_id}", headers=current_user)
    assert persisted.json()["title"] == "Explain diffusion transformers"


def test_titled_chat_streams_do_not_emit_a_title_event(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chat_id = _make_chat_with_credential(client, current_user)
    provider = _TitledProvider(["pong"])
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: provider)

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "hello"},
        headers=current_user,
    ) as response:
        events = parse_sse(response.read().decode())

    assert [event["event"] for event in events][-1] == "message.completed"
    persisted = client.get(f"/chats/{chat_id}", headers=current_user)
    assert persisted.json()["title"] == "SSE chat"


def test_chat_stream_without_credential_returns_422(
    client: TestClient,
    current_user: dict[str, str],
) -> None:
    chat = client.post("/chats", json={"title": "No key"}, headers=current_user)
    assert chat.status_code == 201, chat.text
    response = client.post(
        f"/chats/{chat.json()['id']}/messages/stream",
        json={"content": "hi"},
        headers=current_user,
    )
    assert response.status_code == 422, response.text


def test_live_request_fails_closed_when_hosted_tools_are_disabled(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missed deployment flag must never degrade a live request to model-only chat."""
    chat_id = _make_chat_with_credential(client, current_user)
    monkeypatch.setenv("SINGULARITY_MODAL_ENABLED", "0")
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: _FakeProvider(["unsupported"]))

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "Can you find me Job Postings in past 7 days for New Grad SWE?"},
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        events = parse_sse(response.read().decode())

    assert events[-1]["event"] == "message.error"
    assert events[-1]["data"]["code"] == "tool_evidence_unavailable"
    assert "Modal tools are disabled" in events[-1]["data"]["message"]


def test_chat_stream_surfaces_provider_error_as_terminal_event(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chat_id = _make_chat_with_credential(client, current_user)
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: _FailingProvider([]))

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "trigger error"},
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        events = parse_sse(response.read().decode())

    assert events[-1]["event"] == "message.error"
    assert events[-1]["data"]["code"] == "provider_rate_limited"
    assert events[-1]["data"]["retryable"] is True

    # A failed turn persists only the user message, never a partial assistant reply.
    persisted = client.get(f"/chats/{chat_id}/messages", headers=current_user)
    assert [m["role"] for m in persisted.json()] == ["user"]


@pytest.mark.integration
def test_live_chat_stream_end_to_end_through_the_api(
    client: TestClient,
    current_user: dict[str, str],
) -> None:
    """Real Groq inference through the actual /messages/stream SSE endpoint.

    Opt-in only: set SINGULARITY_RUN_LIVE_TESTS=1 and provide a real Groq key.
    """
    if os.getenv("SINGULARITY_RUN_LIVE_TESTS") != "1":
        pytest.skip("Set SINGULARITY_RUN_LIVE_TESTS=1 to allow live Groq tests")
    api_key = os.getenv("SINGULARITY_TEST_GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        pytest.skip("Set SINGULARITY_TEST_GROQ_API_KEY to run the live chat SSE test")

    credential = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": api_key, "default_model_id": "openai/gpt-oss-20b"},
        headers=current_user,
    )
    assert credential.status_code == 201, credential.text
    chat = client.post(
        "/chats",
        json={"title": "Live", "provider_credential_id": credential.json()["id"]},
        headers=current_user,
    )
    assert chat.status_code == 201, chat.text
    chat_id = chat.json()["id"]

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "Reply with exactly the single word: pong"},
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        events = parse_sse(response.read().decode())

    kinds = [event["event"] for event in events]
    assert kinds[0] == "message.accepted"
    assert kinds[-1] == "message.completed"
    assert kinds.count("message.delta") >= 1
    deltas = [event["data"]["delta"] for event in events if event["event"] == "message.delta"]
    assert "".join(deltas) == events[-1]["data"]["content"]
    assert events[-1]["data"]["content"].strip()

    # The real assistant reply is persisted.
    persisted = client.get(f"/chats/{chat_id}/messages", headers=current_user)
    assert [m["role"] for m in persisted.json()] == ["user", "assistant"]
