from __future__ import annotations

from fastapi.testclient import TestClient


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
