from engine.chat.context import UniversalContextPolicy


def test_universal_policy_uses_one_model_aware_threshold_formula() -> None:
    policy = UniversalContextPolicy()

    assert policy.usable_input_tokens(context_window=32_000, reserved_output_tokens=4_000) == 27_744
    assert policy.summary_trigger_tokens(context_window=32_000, reserved_output_tokens=4_000) == 8_192
    assert policy.summary_output_cap_tokens(context_window=32_000, reserved_output_tokens=4_000) == 1_500


def test_universal_policy_remains_safe_for_small_context_windows() -> None:
    policy = UniversalContextPolicy()

    assert policy.usable_input_tokens(context_window=1_024, reserved_output_tokens=128) == 640
    assert policy.summary_trigger_tokens(context_window=1_024, reserved_output_tokens=128) == 512
    assert policy.summary_output_cap_tokens(context_window=1_024, reserved_output_tokens=128) == 128

