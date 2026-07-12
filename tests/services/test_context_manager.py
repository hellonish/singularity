import asyncio

from api.database import SessionLocal
from api.services.chats import get_chat
from api.services.context import ContextManager
from api.storage.factory import get_object_store


async def _build_snapshot(*, user_id: str, chat_id: str):
    async with SessionLocal() as session:
        chat = await get_chat(session, user_id, chat_id)
        return await ContextManager(session=session, store=get_object_store()).build(chat)


def test_context_manager_uses_report_latest_summary_and_only_newer_messages(
    client,
    current_user: dict[str, str],
) -> None:
    report = client.post("/reports", json={"title": "Research report"}, headers=current_user)
    assert report.status_code == 201
    version = client.post(
        f"/reports/{report.json()['id']}/versions",
        json={"content": "# Findings\nThe report evidence is here."},
        headers=current_user,
    )
    assert version.status_code == 201

    chat = client.post(
        "/chats",
        json={"title": "Report discussion", "report_id": report.json()["id"]},
        headers=current_user,
    )
    assert chat.status_code == 201
    chat_id = chat.json()["id"]

    first = client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "user", "content": "What is the central finding?"},
        headers=current_user,
    )
    second = client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "assistant", "content": "The evidence concerns the main finding."},
        headers=current_user,
    )
    assert first.status_code == second.status_code == 201
    summary = client.post(
        f"/chats/{chat_id}/summaries",
        json={
            "content": "The user asked about the central finding; it concerns the evidence.",
            "through_message_id": second.json()["id"],
            "token_count": 16,
        },
        headers=current_user,
    )
    assert summary.status_code == 201
    third = client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "user", "content": "What are the limitations?"},
        headers=current_user,
    )
    assert third.status_code == 201

    snapshot = asyncio.run(_build_snapshot(user_id=current_user["X-User-ID"], chat_id=chat_id))

    assert snapshot.report is not None
    assert snapshot.report.version_id == version.json()["id"]
    assert snapshot.report.content == "# Findings\nThe report evidence is here."
    assert snapshot.summary is not None
    assert snapshot.summary.id == summary.json()["id"]
    assert [(turn.sequence, turn.role, turn.content) for turn in snapshot.turns] == [
        (third.json()["sequence"], "user", "What are the limitations?"),
    ]
    assert snapshot.latest_message_id == third.json()["id"]


def test_context_manager_selects_the_latest_readable_report_version(client, current_user: dict[str, str]) -> None:
    report = client.post("/reports", json={"title": "Versioned report"}, headers=current_user)
    chat = client.post("/chats", json={"report_id": report.json()["id"]}, headers=current_user)
    first = client.post(
        f"/reports/{report.json()['id']}/versions",
        json={"content": "first version"},
        headers=current_user,
    )
    latest = client.post(
        f"/reports/{report.json()['id']}/versions",
        json={"content": "latest version"},
        headers=current_user,
    )
    assert first.status_code == latest.status_code == 201

    snapshot = asyncio.run(
        _build_snapshot(user_id=current_user["X-User-ID"], chat_id=chat.json()["id"])
    )

    assert snapshot.report is not None
    assert snapshot.report.version_id == latest.json()["id"]
    assert snapshot.report.content == "latest version"
