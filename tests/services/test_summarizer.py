import asyncio
from dataclasses import dataclass

from api.database import SessionLocal
from api.schemas import MessageCreate
from api.services.chats import create_message, get_chat
from api.services.summarizer import GeneratedSummary, Summarizer
from api.storage.factory import get_object_store


@dataclass
class FakeSummaryGenerator:
    content: str = "Compressed conversation memory."
    calls: list[dict] | None = None

    def __post_init__(self) -> None:
        self.calls = []

    async def summarize(self, *, previous_summary, turns, max_output_tokens):
        assert self.calls is not None
        self.calls.append(
            {
                "previous_summary": previous_summary,
                "turn_ids": [turn.id for turn in turns],
                "max_output_tokens": max_output_tokens,
            }
        )
        return GeneratedSummary(content=self.content, token_count=4, metadata={"format": "test"})


class FailingSummaryGenerator:
    async def summarize(self, *, previous_summary, turns, max_output_tokens):
        raise RuntimeError("summary skill unavailable")


async def _summarize(*, user_id: str, chat_id: str, generator: FakeSummaryGenerator):
    async with SessionLocal() as session:
        chat = await get_chat(session, user_id, chat_id)
        return await Summarizer(session=session, store=get_object_store()).summarize_if_needed(
            chat=chat,
            model_id="arbitrary-groq-model",
            context_window=1_024,
            reserved_output_tokens=128,
            generator=generator,
        )


async def _create_message(*, user_id: str, chat_id: str, role: str, content: str):
    async with SessionLocal() as session:
        chat = await get_chat(session, user_id, chat_id)
        return await create_message(session, chat, MessageCreate(role=role, content=content))


def test_summarizer_appends_an_immutable_summary_after_completed_turns_cross_threshold(
    client,
    current_user: dict[str, str],
) -> None:
    chat = client.post("/chats", json={"title": "Summary"}, headers=current_user)
    chat_id = chat.json()["id"]
    user_message = client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "user", "content": "u" * 320},
        headers=current_user,
    )
    assistant_message = client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "assistant", "content": "a" * 320},
        headers=current_user,
    )
    assert user_message.status_code == assistant_message.status_code == 201

    generator = FakeSummaryGenerator()
    summary = asyncio.run(
        _summarize(user_id=current_user["X-User-ID"], chat_id=chat_id, generator=generator)
    )

    assert summary is not None
    assert summary.through_message_id == assistant_message.json()["id"]
    assert summary.summary_data["through_message_sequence"] == assistant_message.json()["sequence"]
    assert summary.summary_data["source_token_count"] >= 640
    assert generator.calls == [
        {
            "previous_summary": None,
            "turn_ids": [user_message.json()["id"], assistant_message.json()["id"]],
            "max_output_tokens": 128,
        }
    ]


def test_summarizer_uses_previous_summary_and_preserves_it_on_success(client, current_user: dict[str, str]) -> None:
    chat = client.post("/chats", json={"title": "Incremental summary"}, headers=current_user)
    chat_id = chat.json()["id"]
    old_user = client.post(
        f"/chats/{chat_id}/messages", json={"role": "user", "content": "old user"}, headers=current_user
    )
    old_assistant = client.post(
        f"/chats/{chat_id}/messages", json={"role": "assistant", "content": "old assistant"}, headers=current_user
    )
    old_summary = client.post(
        f"/chats/{chat_id}/summaries",
        json={"content": "Original immutable memory.", "through_message_id": old_assistant.json()["id"]},
        headers=current_user,
    )
    new_user = asyncio.run(
        _create_message(
            user_id=current_user["X-User-ID"], chat_id=chat_id, role="user", content="u" * 320
        )
    )
    new_assistant = asyncio.run(
        _create_message(
            user_id=current_user["X-User-ID"], chat_id=chat_id, role="assistant", content="a" * 320
        )
    )
    assert all(response.status_code == 201 for response in (old_user, old_assistant, old_summary))
    assert new_user.sequence < new_assistant.sequence

    generator = FakeSummaryGenerator(content="New immutable memory.")
    created = asyncio.run(
        _summarize(user_id=current_user["X-User-ID"], chat_id=chat_id, generator=generator)
    )

    assert created is not None
    assert generator.calls and generator.calls[0]["previous_summary"] == "Original immutable memory."
    summaries = client.get(f"/chats/{chat_id}/summaries", headers=current_user).json()
    assert [summary["content"] for summary in summaries] == [
        "Original immutable memory.",
        "New immutable memory.",
    ]


def test_summarizer_does_not_run_before_an_assistant_response(client, current_user: dict[str, str]) -> None:
    chat = client.post("/chats", json={"title": "Pending response"}, headers=current_user)
    chat_id = chat.json()["id"]
    client.post(
        f"/chats/{chat_id}/messages",
        json={"role": "user", "content": "u" * 800},
        headers=current_user,
    )

    generator = FakeSummaryGenerator()
    summary = asyncio.run(
        _summarize(user_id=current_user["X-User-ID"], chat_id=chat_id, generator=generator)
    )

    assert summary is None
    assert generator.calls == []


def test_failed_incremental_summary_leaves_the_previous_summary_active(client, current_user: dict[str, str]) -> None:
    chat = client.post("/chats", json={"title": "Summary recovery"}, headers=current_user)
    chat_id = chat.json()["id"]
    old_user = client.post(
        f"/chats/{chat_id}/messages", json={"role": "user", "content": "old"}, headers=current_user
    )
    old_assistant = client.post(
        f"/chats/{chat_id}/messages", json={"role": "assistant", "content": "old reply"}, headers=current_user
    )
    old_summary = client.post(
        f"/chats/{chat_id}/summaries",
        json={"content": "Stable prior memory.", "through_message_id": old_assistant.json()["id"]},
        headers=current_user,
    )
    asyncio.run(
        _create_message(user_id=current_user["X-User-ID"], chat_id=chat_id, role="user", content="u" * 320)
    )
    asyncio.run(
        _create_message(user_id=current_user["X-User-ID"], chat_id=chat_id, role="assistant", content="a" * 320)
    )
    assert all(response.status_code == 201 for response in (old_user, old_assistant, old_summary))

    try:
        asyncio.run(
            _summarize(
                user_id=current_user["X-User-ID"], chat_id=chat_id, generator=FailingSummaryGenerator()
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "summary skill unavailable"
    else:
        raise AssertionError("expected the summary generator failure")

    summaries = client.get(f"/chats/{chat_id}/summaries", headers=current_user).json()
    assert [summary["content"] for summary in summaries] == ["Stable prior memory."]
