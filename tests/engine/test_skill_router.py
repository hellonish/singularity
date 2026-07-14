from engine.chat.skill_router import select_skills
from engine.tools.contracts import chat_planner_tool_schemas


def test_skill_router_shortlists_code_tools_without_exposing_unrelated_domains() -> None:
    selected = select_skills("Write and execute a Python script, then run tests")
    schemas, bindings = chat_planner_tool_schemas(
        allowed_execution_kinds=("trusted_function", "sandbox"),
        skill_ids=selected.ids,
    )
    tools = {tool for _, tool in bindings.values()}

    assert selected.ids[0] == "code_execution"
    assert "code_execution" in tools
    assert "pubmed" not in tools
    assert len(selected.ids) <= 3
    assert schemas
