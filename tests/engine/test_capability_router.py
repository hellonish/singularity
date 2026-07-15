from engine.chat.capability_router import select_capability
from engine.research_workflow.preparation import validated_execution_requirements


def test_repository_url_selects_required_sandbox() -> None:
    decision = select_capability("Research https://github.com/openai/openai-python/tree/main")
    assert decision.kind == "sandbox"
    assert decision.required is True
    assert decision.repository_url == "https://github.com/openai/openai-python"
    assert decision.skill_ids == ("repository_inspection", "sandbox_workspace")


def test_dataset_and_code_select_sandbox_but_conversation_does_not() -> None:
    assert select_capability("Analyze this CSV dataset").skill_ids[0] == "dataset_analysis"
    assert select_capability("Execute this Python script").skill_ids[0] == "code_execution"
    assert select_capability("Explain transformers").kind == "none"


def test_tenant_report_retrieval_stays_api_only() -> None:
    assert select_capability("Search my report for the revenue number").kind == "api_only"


def test_research_requirement_uses_only_url_from_original_request() -> None:
    requirements = validated_execution_requirements(
        "Build and test https://github.com/openai/openai-python/tree/main",
        ["Inspect package layout"],
    )
    assert len(requirements) == 1
    requirement = requirements[0]
    assert requirement.kind == "repository"
    assert requirement.resource_reference == "https://github.com/openai/openai-python"
    assert requirement.profile == "repository_build"
    assert "run_checks" in requirement.actions


def test_inline_code_and_csv_inputs_are_server_validated_for_research() -> None:
    code = validated_execution_requirements("Run this code:\n```python\nprint(42)\n```")[0]
    assert code.resource_reference.startswith("inline://sha256/")
    assert code.validated_arguments == {
        "files": {"main.py": "print(42)"},
        "command": ["python", "main.py"],
    }

    dataset = validated_execution_requirements(
        "Analyze this CSV dataset:\n```csv\na,b\n1,2\n```"
    )[0]
    assert dataset.kind == "dataset"
    assert dataset.validated_arguments["dataset_csv"] == "a,b\n1,2"
    assert "pd.read_csv" in dataset.validated_arguments["python_code"]
