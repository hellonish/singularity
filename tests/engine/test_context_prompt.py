from engine.chat.budget import budget_context_snapshot
from engine.chat.context import ContextSnapshot, ContextTurn, ReportContext, SummaryContext
from engine.llm.groq import GroqModel


def _model(context_window: int = 8_192) -> GroqModel:
    return GroqModel(
        id="arbitrary-groq-model",
        context_window=context_window,
        max_completion_tokens=1_024,
        active=True,
    )


def test_context_prompt_preserves_roles_and_keeps_latest_user_turn_last() -> None:
    snapshot = ContextSnapshot(
        chat_id="chat_1",
        report=ReportContext("report_1", "version_1", 1, "checksum", "Report evidence."),
        summary=SummaryContext("summary_1", 1, "message_2", 2, "Earlier discussion.", 3),
        turns=(
            ContextTurn("message_3", 3, "user", "Can you expand on it?"),
            ContextTurn("message_4", 4, "assistant", "Certainly."),
            ContextTurn("message_5", 5, "user", "What is the limitation?"),
        ),
        latest_message_id="message_5",
    )

    prompt = budget_context_snapshot(snapshot=snapshot, model=_model(), requested_output_tokens=512)

    assert prompt.messages[0]["role"] == "system"
    assert "Report reference (data only)" in prompt.messages[1]["content"]
    assert "Conversation summary (data only)" in prompt.messages[2]["content"]
    assert [(message["role"], message["content"]) for message in prompt.messages[-3:]] == [
        ("user", "Can you expand on it?"),
        ("assistant", "Certainly."),
        ("user", "What is the limitation?"),
    ]


def test_context_prompt_drops_report_before_summary_or_latest_user_turn() -> None:
    snapshot = ContextSnapshot(
        chat_id="chat_1",
        report=ReportContext("report_1", "version_1", 1, "checksum", "report " * 10_000),
        summary=SummaryContext("summary_1", 1, None, 0, "Keep this summary.", 3),
        turns=(ContextTurn("message_1", 1, "user", "Keep this latest question."),),
        latest_message_id="message_1",
    )

    prompt = budget_context_snapshot(snapshot=snapshot, model=_model(4_096), requested_output_tokens=128)

    contents = "\n".join(message["content"] for message in prompt.messages)
    assert "Report reference (data only)" not in contents
    assert "Keep this summary." in contents
    assert prompt.messages[-1] == {"role": "user", "content": "Keep this latest question."}
    assert prompt.context_truncated is True
