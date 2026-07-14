from engine.chat.caps import choose_agent_step_budget
from engine.chat.effort import ChatEffort


def test_agent_selects_task_sized_step_budget_within_effort_cap() -> None:
    instant = choose_agent_step_budget(
        "Search current sources and compare multiple sources", ChatEffort.INSTANT
    )
    medium_code = choose_agent_step_budget(
        "Write code, execute it, debug the failing tests, and verify the result", ChatEffort.MEDIUM
    )
    ultra_simple = choose_agent_step_budget("Say hello", ChatEffort.ULTRA)

    assert instant.selected_steps == instant.hard_cap == 4
    assert medium_code.selected_steps == medium_code.hard_cap == 10
    assert ultra_simple.selected_steps == 2
