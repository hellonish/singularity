import asyncio
from dataclasses import dataclass

from api.services.summary_scheduler import SummaryScheduler
from api.storage.factory import get_object_store


@dataclass
class FakeSummaryGenerator:
    async def summarize(self, *, previous_summary, turns, max_output_tokens):
        from api.services.summarizer import GeneratedSummary

        return GeneratedSummary(content="Compressed conversation memory.", token_count=4)


def test_scheduler_runs_summary_work_asynchronously_after_a_completed_turn(client, current_user: dict[str, str]) -> None:
    chat = client.post("/chats", json={"title": "Scheduled summary"}, headers=current_user)
    chat_id = chat.json()["id"]
    user_message = client.post(
        f"/chats/{chat_id}/messages", json={"role": "user", "content": "u" * 320}, headers=current_user
    )
    assistant_message = client.post(
        f"/chats/{chat_id}/messages", json={"role": "assistant", "content": "a" * 320}, headers=current_user
    )
    assert user_message.status_code == assistant_message.status_code == 201

    generator = FakeSummaryGenerator()
    scheduler = SummaryScheduler(generator=generator, store=get_object_store())

    async def run() -> None:
        task = scheduler.schedule(
            user_id=current_user["X-User-ID"],
            chat_id=chat_id,
            model_id="arbitrary-groq-model",
            context_window=1_024,
            reserved_output_tokens=128,
        )
        assert not task.done()
        summary = await task
        assert summary is not None

        # Re-running after the coverage boundary advances is a no-op.
        assert await scheduler.run_once(
            user_id=current_user["X-User-ID"],
            chat_id=chat_id,
            model_id="arbitrary-groq-model",
            context_window=1_024,
            reserved_output_tokens=128,
        ) is None

    asyncio.run(run())

    summaries = client.get(f"/chats/{chat_id}/summaries", headers=current_user).json()
    assert [summary["content"] for summary in summaries] == ["Compressed conversation memory."]
