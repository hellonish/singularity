from __future__ import annotations

from fastapi.testclient import TestClient


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
