from __future__ import annotations

from fastapi.testclient import TestClient

from api.config import settings
from api.routers import research as research_router


def test_health_and_core_persistence_flow(client: TestClient, current_user: dict[str, str]) -> None:
    assert client.get("/health").status_code == 200

    chat = client.post("/chats", json={"title": "Architecture"}, headers=current_user)
    assert chat.status_code == 201, chat.text
    chat_id = chat.json()["id"]

    message = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Explain the design"},
        headers=current_user,
    )
    assert message.status_code == 201, message.text
    assert message.json()["sequence"] == 1

    report = client.post("/reports", json={"title": "Design report"}, headers=current_user)
    assert report.status_code == 201, report.text
    report_id = report.json()["id"]

    version = client.post(
        f"/reports/{report_id}/versions",
        json={"content": "# Design"},
        headers=current_user,
    )
    assert version.status_code == 201, version.text
    assert version.json()["content"] is None
    assert version.json()["content_uri"].startswith("local://reports/")

    content = client.get(
        f"/reports/{report_id}/versions/{version.json()['id']}/content",
        headers=current_user,
    )
    assert content.status_code == 200
    assert content.text == "# Design"


def test_research_run_persists_caps_and_queued_event(client: TestClient, current_user: dict[str, str], monkeypatch) -> None:
    async def enqueue(_run_id: str) -> bool:
        return True

    monkeypatch.setattr(settings, "research_worker_enabled", True)
    monkeypatch.setattr(research_router, "enqueue_research_run", enqueue)
    credential = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": "gsk_test_research_run"},
        headers=current_user,
    )
    assert credential.status_code == 201, credential.text
    response = client.post(
        "/research/runs",
        json={
            "query": "How does bounded research work?",
            "strength": 2,
            "provider_credential_id": credential.json()["id"],
        },
        headers=current_user,
    )
    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["run_data"]["caps"]["max_qa_suggestions_per_section"] == 2
    assert payload["run_data"]["caps"]["max_tool_calls_per_node"] == 4

    cancelled = client.post(f"/research/runs/{payload['id']}/cancel", headers=current_user)
    assert cancelled.status_code == 200, cancelled.text
    replay = client.get(
        f"/research/runs/{payload['id']}/events",
        headers={**current_user, "Last-Event-ID": "1"},
    )
    assert replay.status_code == 200
    assert "event: research.cancelled" in replay.text
    assert "id: 2" in replay.text
    assert "event: research.completed" not in replay.text
