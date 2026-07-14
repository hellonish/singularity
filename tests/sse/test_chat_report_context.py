"""A report-linked chat injects report context alongside prior conversation."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.services.report_context import ingest_report_content
from api.services.report_context_errors import LOAD_MESSAGE
from engine.llm.groq import GroqModel
from tests.sse.helpers import parse_sse
from vector_store import VectorStoreClient


class FakeEmbedder:
    def embed(self, text: str) -> list[float]:
        return [0.1] * 384

    def chunk_and_embed(self, text: str) -> list[tuple[str, list[float]]]:
        return [(text, self.embed(text))]


class _CapturingProvider:
    """Records the messages the agent sends so we can assert on the prompt."""

    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    async def retrieve_model(self, *, api_key: str, model_id: str) -> GroqModel:
        return GroqModel(id=model_id, context_window=8_192, max_completion_tokens=1_024, active=True)

    async def stream_chat(self, *, api_key: str, config, messages):
        self.messages = list(messages)
        yield "ok"


def _make_report_chat(client: TestClient, headers: dict[str, str]) -> tuple[str, str]:
    credential = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": "gsk_test_not_a_real_key", "default_model_id": "openai/gpt-oss-20b"},
        headers=headers,
    )
    assert credential.status_code == 201, credential.text
    report = client.post("/reports", json={"title": "Attached report"}, headers=headers)
    assert report.status_code == 201, report.text
    report_id = report.json()["id"]
    chat = client.post(
        "/chats",
        json={
            "title": "Report chat",
            "provider_credential_id": credential.json()["id"],
            "report_id": report_id,
        },
        headers=headers,
    )
    assert chat.status_code == 201, chat.text
    return chat.json()["id"], report_id


def test_report_linked_chat_injects_report_context_into_the_prompt(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chat_id, report_id = _make_report_chat(client, current_user)

    store = VectorStoreClient(force_in_memory=True, embedder=FakeEmbedder())
    ingest_report_content(
        store,
        user_id=current_user["X-User-ID"],
        report_id=report_id,
        version_number=1,
        content="The bridge failed because of corrosion in the primary support cables.",
        title="Bridge report",
    )

    provider = _CapturingProvider()
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: provider)
    monkeypatch.setattr("api.services.chat_stream.get_vector_store", lambda: store)

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "Why did the bridge fail?"},
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        events = parse_sse(response.read().decode())

    assert events[-1]["event"] == "message.completed"
    prompt_text = " ".join(part["content"] for part in provider.messages)
    assert "corrosion in the primary support cables" in prompt_text


def test_chat_without_report_does_not_touch_the_vector_store(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": "gsk_test_not_a_real_key", "default_model_id": "openai/gpt-oss-20b"},
        headers=current_user,
    )
    chat = client.post(
        "/chats",
        json={"title": "No report", "provider_credential_id": credential.json()["id"]},
        headers=current_user,
    )
    chat_id = chat.json()["id"]

    provider = _CapturingProvider()
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: provider)

    def _fail() -> None:
        raise AssertionError("vector store must not be consulted for a report-less chat")

    monkeypatch.setattr("api.services.chat_stream.get_vector_store", _fail)

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "hello"},
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        events = parse_sse(response.read().decode())

    assert events[-1]["event"] == "message.completed"


class _ExplodingVectorStore:
    """Stands in for an unreachable vector store."""

    def search(self, *, scope, query_text, limit=8, min_credibility=0.0):
        raise ConnectionError("qdrant unreachable at http://localhost:6333")


def test_report_context_failure_fails_the_turn_with_a_generic_load_message(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    chat_id, _report_id = _make_report_chat(client, current_user)

    provider = _CapturingProvider()
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: provider)
    monkeypatch.setattr("api.services.chat_stream.get_vector_store", _ExplodingVectorStore)

    with caplog.at_level("ERROR"):
        with client.stream(
            "POST",
            f"/chats/{chat_id}/messages/stream",
            json={"content": "Why did the bridge fail?"},
            headers=current_user,
        ) as response:
            assert response.status_code == 200, response.text
            events = parse_sse(response.read().decode())

    # The user sees only a generic, retryable load message — never the report,
    # never a partial answer, never infrastructure detail.
    assert [event["event"] for event in events] == ["message.error"]
    error = events[0]["data"]
    assert error["message"] == LOAD_MESSAGE
    assert error["code"] == "report_context_unavailable"
    assert error["retryable"] is True
    assert "qdrant" not in error["message"].lower()

    # The provider was never called: no confidently-wrong answer was generated.
    assert provider.messages == []

    # The real cause is logged in full for operators.
    assert any("report context retrieval failed" in record.message for record in caplog.records)
    assert any("qdrant unreachable" in record.getMessage() for record in caplog.records)


def test_report_context_failure_persists_only_the_user_message(
    client: TestClient,
    current_user: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chat_id, _report_id = _make_report_chat(client, current_user)
    monkeypatch.setattr("api.services.chat_stream.provider_for", lambda name: _CapturingProvider())
    monkeypatch.setattr("api.services.chat_stream.get_vector_store", _ExplodingVectorStore)

    with client.stream(
        "POST",
        f"/chats/{chat_id}/messages/stream",
        json={"content": "Why did the bridge fail?"},
        headers=current_user,
    ) as response:
        response.read()

    persisted = client.get(f"/chats/{chat_id}/messages", headers=current_user)
    assert [m["role"] for m in persisted.json()] == ["user"]
