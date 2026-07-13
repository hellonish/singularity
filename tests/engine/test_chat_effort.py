from engine.chat.effort import ChatEffort, chat_output_budget, get_chat_effort_profile, reasoning_effort_for_model


def test_effort_profiles_match_the_chat_effort_map() -> None:
    instant = get_chat_effort_profile(ChatEffort.INSTANT)
    medium = get_chat_effort_profile(ChatEffort.MEDIUM)
    high = get_chat_effort_profile(ChatEffort.HIGH)
    ultra = get_chat_effort_profile(ChatEffort.ULTRA)

    assert (instant.max_agent_tool_steps, instant.max_output_tokens, instant.timeout_seconds) == (2, 700, 20)
    assert (medium.max_agent_tool_steps, medium.max_output_tokens, medium.timeout_seconds) == (6, 1_300, 60)
    assert (high.max_recent_raw_context_tokens, high.max_document_chunks, high.max_files) == (24_000, 10, 10)
    assert (ultra.max_recent_raw_context_tokens, ultra.max_old_messages, ultra.max_calls_per_tool_type) == (
        48_000,
        15,
        8,
    )
    assert ultra.compaction_trigger_percent == 0.88


def test_reasoning_effort_is_sent_for_supported_reasoning_models() -> None:
    assert reasoning_effort_for_model("openai/gpt-oss-20b", ChatEffort.INSTANT) == "low"
    assert reasoning_effort_for_model("openai/gpt-oss-120b", ChatEffort.MEDIUM) == "medium"
    assert reasoning_effort_for_model("openai/gpt-oss-20b", ChatEffort.ULTRA) == "high"
    assert reasoning_effort_for_model("deepseek/deepseek-r1", ChatEffort.INSTANT) == "low"
    assert reasoning_effort_for_model("llama-3.3-70b-versatile", ChatEffort.HIGH) is None
    assert chat_output_budget("deepseek/deepseek-r1", 500) == 1_200
    assert chat_output_budget("llama-3.3-70b-versatile", 500) == 500
