from __future__ import annotations

from fastapi.testclient import TestClient

from tests.sse.helpers import parse_sse


def test_chat_message_stream_emits_ordered_sse_events(
    client: TestClient,
    current_user: dict[str, str],
) -> None:
    chat = client.post("/chats", json={"title": "SSE chat"}, headers=current_user)
    assert chat.status_code == 201, chat.text

    with client.stream(
        "POST",
        f"/chats/{chat.json()['id']}/messages/stream",
        json={"content": "Stream a response"},
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
        events = parse_sse(response.read().decode())

    assert [event["event"] for event in events] == [
        "message.accepted",
        "message.delta",
        "message.delta",
        "message.delta",
        "message.completed",
    ]
    assert "".join(event["data"]["delta"] for event in events[1:-1]) == events[-1]["data"]["content"]
    assert all(event["id"] for event in events)

    persisted = client.get(f"/chats/{chat.json()['id']}/messages", headers=current_user)
    assert persisted.status_code == 200
    assert [message["content"] for message in persisted.json()] == ["Stream a response"]
