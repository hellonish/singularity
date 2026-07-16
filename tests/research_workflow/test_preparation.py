import pytest
from pydantic import ValidationError

from engine.entity_resolution import EntityRef, EntityResolutionStatus, EntityScope
from engine.research_workflow.preparation import (
    ClarificationQuestion,
    ResearchBrief,
    ensure_ask_question,
    parse_final_brief,
)


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
    capped = ResearchBrief(
        refined_objective="Too many questions",
        plan_points=_plan(),
        questions=[
            ClarificationQuestion(question_id=f"q{index}", text=f"Question {index}")
            for index in range(5)
        ],
    )
    assert len(capped.questions) == 4


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


def test_brief_tolerates_provider_metadata_and_normalizes_questions():
    brief = ResearchBrief.model_validate({
        "refined_objective": "Research the supplied repository",
        "plan_points": [
            "Resolve the repository",
            "Inspect primary sources",
            "Compare evidence",
            "Write the report",
            "Check citations",
            "This sixth pointer is trimmed",
        ],
        "questions": [
            "Which audience should the report prioritize?",
            {"id": "format", "question": "Which output format?", "rationale": "Shapes delivery"},
        ],
        "deliverable": {"format": "Markdown report"},
        "entity_scope": {
            "status": "confirmed",
            "resolution_mode": "AUTO",
            "entities": [{
                "name": "hellonish/singularity",
                "surface_name": "Singularity",
                "identifiers": [{"type": "url", "value": "https://github.com/hellonish/singularity"}],
                "confidence": "98%",
                "provider_rationale": "The URL is definitive",
            }],
            "provider_notes": "extra metadata is not part of the runtime contract",
        },
        "provider_notes": "ignored",
    })

    assert len(brief.plan_points) == 5
    assert brief.questions[0].question_id == "q1"
    assert brief.questions[1].question_id == "format"
    assert brief.deliverable == "Markdown report"
    assert brief.entity_scope.status == EntityResolutionStatus.RESOLVED
    assert brief.entity_scope.resolution_mode == "auto"
    assert brief.entity_scope.entities[0].entity_id == "hellonish_singularity"
    assert brief.entity_scope.entities[0].confidence == 0.98


def test_final_brief_keeps_the_validated_plan_when_model_returns_only_entity_scope():
    draft = ResearchBrief(
        refined_objective="Analyze the supplied repository",
        plan_points=_plan(),
        deliverable="Cited repository report",
    )

    final = parse_final_brief(
        '{"entity_scope":{"status":"resolved","resolution_mode":"auto","entities":[{"name":"hellonish/singularity","identifiers":["https://github.com/hellonish/singularity"]}]}}',
        draft,
    )

    assert final.refined_objective == draft.refined_objective
    assert final.plan_points == draft.plan_points
    assert final.entity_scope.status == EntityResolutionStatus.RESOLVED
    assert final.entity_scope.entities[0].canonical_name == "hellonish/singularity"
