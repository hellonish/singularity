import pytest
from pydantic import ValidationError

from engine.tools.contracts import ChatToolInvocation, chat_planner_tool_schemas, validate_chat_tool_invocation


def test_skill_scoped_tool_invocation_accepts_only_registered_tools() -> None:
    invocation = ChatToolInvocation(
        run_id="run_1",
        skill_id="medical_research",
        tool_name="pubmed",
        query="GLP-1 obesity trial",
        arguments={"max_results": 5},
        timeout_seconds=60,
    )

    validated = validate_chat_tool_invocation(invocation)

    assert validated.tool_name == "pubmed"
    assert validated.arguments == {"max_results": 5}


def test_skill_scoped_tool_invocation_rejects_tool_not_allowed_by_skill() -> None:
    invocation = ChatToolInvocation(
        run_id="run_1",
        skill_id="medical_research",
        tool_name="sec_edgar",
        query="revenue",
        arguments={},
        timeout_seconds=60,
    )

    with pytest.raises(ValueError, match="not allowed"):
        validate_chat_tool_invocation(invocation)


def test_tool_argument_contract_rejects_unknown_arguments() -> None:
    invocation = ChatToolInvocation(
        run_id="run_1",
        skill_id="medical_research",
        tool_name="pubmed",
        query="trial",
        arguments={"max_results": 5, "unsafe": "no"},
        timeout_seconds=60,
    )

    with pytest.raises(ValidationError):
        validate_chat_tool_invocation(invocation)


def test_cli_planner_exposes_trusted_functions_but_not_sandbox_or_api_only_tools() -> None:
    schemas, bindings = chat_planner_tool_schemas()
    tool_names = {tool_name for _, tool_name in bindings.values()}

    assert "web_search" in tool_names
    assert "calculator" in tool_names
    assert "repository_inspection" not in tool_names
    assert "dataset_analysis" not in tool_names
    assert "production_retrieval" not in tool_names
    assert schemas
