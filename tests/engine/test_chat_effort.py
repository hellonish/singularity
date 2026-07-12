from engine.chat.effort import ChatEffort, get_chat_effort_profile, reasoning_effort_for_model


def test_effort_profiles_match_the_chat_effort_map() -> None:
    instant = get_chat_effort_profile(ChatEffort.INSTANT)
    medium = get_chat_effort_profile(ChatEffort.MEDIUM)
    high = get_chat_effort_profile(ChatEffort.HIGH)
    ultra = get_chat_effort_profile(ChatEffort.ULTRA)

    assert (instant.max_agent_tool_steps, instant.max_output_tokens, instant.timeout_seconds) == (1, 500, 20)
    assert (medium.max_agent_tool_steps, medium.max_output_tokens, medium.timeout_seconds) == (4, 1_500, 60)
    assert (high.max_recent_raw_context_tokens, high.max_document_chunks, high.max_files) == (24_000, 10, 10)
    assert (ultra.max_recent_raw_context_tokens, ultra.max_old_messages, ultra.max_calls_per_tool_type) == (
        48_000,
        15,
        8,
    )
    assert ultra.compaction_trigger_percent == 0.88


def test_reasoning_effort_is_only_sent_for_gpt_oss_models() -> None:
    assert reasoning_effort_for_model("openai/gpt-oss-20b", ChatEffort.INSTANT) == "low"
    assert reasoning_effort_for_model("openai/gpt-oss-120b", ChatEffort.MEDIUM) == "medium"
    assert reasoning_effort_for_model("openai/gpt-oss-20b", ChatEffort.ULTRA) == "high"
    assert reasoning_effort_for_model("llama-3.3-70b-versatile", ChatEffort.HIGH) is None
