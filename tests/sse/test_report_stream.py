from __future__ import annotations

from fastapi.testclient import TestClient

from tests.sse.helpers import parse_sse


def test_report_stream_emits_ordered_sse_events(
    client: TestClient,
    current_user: dict[str, str],
) -> None:
    report = client.post("/reports", json={"title": "SSE report"}, headers=current_user)
    assert report.status_code == 201, report.text

    with client.stream(
        "GET",
        f"/reports/{report.json()['id']}/stream",
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["x-accel-buffering"] == "no"
        events = parse_sse(response.read().decode())

    assert [event["event"] for event in events] == [
        "report.started",
        "report.delta",
        "report.delta",
        "report.delta",
        "report.completed",
    ]
    assert "".join(event["data"]["delta"] for event in events[1:-1]) == events[-1]["data"]["content"]
    assert events[-1]["data"]["content"].startswith("# SSE report")
