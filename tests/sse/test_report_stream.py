from __future__ import annotations

from fastapi.testclient import TestClient

from tests.sse.helpers import parse_sse


_REPORT_MARKDOWN = "# SSE report\n\n## Summary\n\nReal stored report content.\n"


def test_report_stream_replays_the_latest_stored_version(
    client: TestClient,
    current_user: dict[str, str],
) -> None:
    report = client.post("/reports", json={"title": "SSE report"}, headers=current_user)
    assert report.status_code == 201, report.text
    report_id = report.json()["id"]

    version = client.post(
        f"/reports/{report_id}/versions",
        json={"content": _REPORT_MARKDOWN, "content_format": "markdown"},
        headers=current_user,
    )
    assert version.status_code == 201, version.text

    with client.stream(
        "GET",
        f"/reports/{report_id}/stream",
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["x-accel-buffering"] == "no"
        events = parse_sse(response.read().decode())

    assert events[0]["event"] == "report.started"
    assert events[-1]["event"] == "report.completed"
    deltas = [event["data"]["delta"] for event in events if event["event"] == "report.delta"]
    assert deltas, "expected at least one report.delta"
    assert "".join(deltas) == events[-1]["data"]["content"] == _REPORT_MARKDOWN


def test_report_stream_emits_pending_when_no_version_exists(
    client: TestClient,
    current_user: dict[str, str],
) -> None:
    report = client.post("/reports", json={"title": "Pending report"}, headers=current_user)
    assert report.status_code == 201, report.text

    with client.stream(
        "GET",
        f"/reports/{report.json()['id']}/stream",
        headers=current_user,
    ) as response:
        assert response.status_code == 200, response.text
        events = parse_sse(response.read().decode())

    assert [event["event"] for event in events] == ["report.started", "report.pending"]
