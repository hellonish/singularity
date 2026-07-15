import pytest
from pydantic import ValidationError

from engine.entity_resolution import EntityRef, EntityResolutionStatus, EntityScope
from engine.research_workflow.preparation import ClarificationQuestion, ResearchBrief, ensure_ask_question


def _plan() -> list[str]:
    return ["Define scope", "Gather evidence", "Compare findings", "Write the report"]


def test_research_brief_enforces_four_to_five_plan_points_and_four_question_cap():
    brief = ResearchBrief(
        refined_objective="Compare the selected company with its peers",
        plan_points=_plan(),
        questions=[ClarificationQuestion(question_id="q1", text="Which market?", reason="Sets scope")],
    )
    assert len(brief.plan_points) == 4

    with pytest.raises(ValidationError):
        ResearchBrief(refined_objective="Too short", plan_points=["One", "Two", "Three"])
    with pytest.raises(ValidationError):
        ResearchBrief(
            refined_objective="Too many questions",
            plan_points=_plan(),
            questions=[
                ClarificationQuestion(question_id=f"q{index}", text=f"Question {index}")
                for index in range(5)
            ],
        )


def test_ask_mode_repairs_missing_entity_question_but_auto_can_select():
    entity = EntityRef(
        entity_id="acme", mention="Acme", canonical_name="Acme", confidence=0,
    )
    ask = ensure_ask_question(ResearchBrief(
        refined_objective="Research Acme",
        plan_points=_plan(),
        entity_scope=EntityScope(
            status=EntityResolutionStatus.AMBIGUOUS,
            entities=[entity],
            resolution_mode="ask",
        ),
    ))
    assert ask.questions and "Which Acme" in ask.questions[0].text

    auto = ResearchBrief(
        refined_objective="Research Acme",
        plan_points=_plan(),
        entity_scope=EntityScope(
            status=EntityResolutionStatus.AMBIGUOUS,
            entities=[entity],
            resolution_mode="auto",
        ),
    )
    assert auto.questions == []


def test_brief_accepts_structured_plan_and_constraint_values_from_provider():
    brief = ResearchBrief.model_validate({
        "refined_objective": "Research the repository",
        "plan_points": [
            {"step": "Resolve the repository"},
            {"text": "Inspect primary sources"},
            {"point": "Compare evidence"},
            {"value": "Write the report"},
        ],
        "must_haves": [{"requirement": "Use the official repository"}],
        "assumptions": [{"assumption": "The supplied URL is authoritative"}],
    })
    assert brief.plan_points == [
        "Resolve the repository", "Inspect primary sources", "Compare evidence", "Write the report",
    ]
    assert brief.must_haves == ["Use the official repository"]
