from __future__ import annotations

from fastapi.testclient import TestClient

from api.config import settings
from api.routers import research as research_router
from api.services.auth import create_access_token


def test_fourth_message_in_a_second_is_rejected(client: TestClient, current_user: dict[str, str]) -> None:
    chat = client.post("/chats", json={"title": "Limited"}, headers=current_user)
    assert chat.status_code == 201
    path = f"/chats/{chat.json()['id']}/messages"

    for _ in range(3):
        assert client.post(path, json={"content": "hello"}, headers=current_user).status_code == 201

    blocked = client.post(path, json={"content": "blocked"}, headers=current_user)
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "1"


def test_chat_and_report_creation_limits_are_enforced(client: TestClient, current_user: dict[str, str]) -> None:
    for _ in range(3):
        assert client.post("/chats", json={"title": "chat"}, headers=current_user).status_code == 201
    assert client.post("/chats", json={"title": "blocked"}, headers=current_user).status_code == 429

    assert client.post("/reports", json={"title": "first"}, headers=current_user).status_code == 201
    assert client.post("/reports", json={"title": "blocked"}, headers=current_user).status_code == 429


def test_bearer_authenticated_cli_requests_are_rate_limited(
    client: TestClient, monkeypatch
) -> None:
    user = client.post("/users", json={"display_name": "CLI limiter"}).json()
    monkeypatch.setattr(settings, "auth_mode", "bearer")
    monkeypatch.setattr(settings, "jwt_secret", "rate-limit-secret")
    access_token, _ = create_access_token(user["id"])
    headers = {"Authorization": f"Bearer {access_token}"}

    for _ in range(3):
        assert client.post("/chats", json={"title": "chat"}, headers=headers).status_code == 201
    assert client.post("/chats", json={"title": "blocked"}, headers=headers).status_code == 429


def test_research_run_creation_has_a_separate_hourly_limit(client: TestClient, current_user: dict[str, str], monkeypatch) -> None:
    async def enqueue(_run_id: str) -> bool:
        return True

    monkeypatch.setattr(settings, "research_worker_enabled", True)
    monkeypatch.setattr(research_router, "enqueue_research_run", enqueue)
    credential = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": "gsk_test_research_rate"},
        headers=current_user,
    )
    assert credential.status_code == 201
    body = {"query": "bounded research", "provider_credential_id": credential.json()["id"]}
    for _ in range(3):
        assert client.post("/research/runs", json=body, headers=current_user).status_code == 202
    blocked = client.post("/research/runs", json=body, headers=current_user)
    assert blocked.status_code == 429
