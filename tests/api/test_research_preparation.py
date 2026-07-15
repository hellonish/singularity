from fastapi.testclient import TestClient

from api.config import settings
from api.models import ResearchPreparation
from api.routers import research as research_router


def _brief() -> dict:
    return {
        "refined_objective": "Research the identified Acme technology company",
        "plan_points": [
            "Confirm the company identity",
            "Collect primary sources",
            "Compare the evidence",
            "Write the cited report",
        ],
        "questions": [{
            "question_id": "identity",
            "text": "What is Acme's official website?",
            "reason": "It separates the target from namesakes.",
        }],
        "must_haves": [],
        "deliverable": "Research report",
        "entity_scope": {"status": "ambiguous", "entities": [], "relationship_constraints": [], "resolution_mode": "ask", "assumptions": []},
        "assumptions": [],
    }


def test_ask_preparation_answers_only_current_question_and_becomes_ready(
    client: TestClient, current_user: dict[str, str], monkeypatch
) -> None:
    async def prepare(session, user, body):
        preparation = ResearchPreparation(
            user_id=user.id,
            provider_credential_id=body.provider_credential_id,
            query=body.query,
            approval_mode="ask",
            status="awaiting_input",
            model_id=body.model_id,
            strength=body.strength,
            plan_data=_brief(),
        )
        session.add(preparation)
        await session.commit()
        await session.refresh(preparation)
        return preparation, None

    async def finalize(session, _user, preparation):
        final = {**preparation.plan_data, "questions": [], "entity_scope": {
            "status": "resolved", "entities": [], "relationship_constraints": [],
            "resolution_mode": "ask", "assumptions": [],
        }}
        preparation.final_brief = final
        preparation.status = "ready"
        await session.commit()
        await session.refresh(preparation)
        return preparation

    monkeypatch.setattr(settings, "research_worker_enabled", True)
    monkeypatch.setattr(research_router, "prepare_research", prepare)
    monkeypatch.setattr(research_router, "finalize_after_answers", finalize)

    credential = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": "gsk_research_preparation_test"},
        headers=current_user,
    )
    assert credential.status_code == 201, credential.text

    created = client.post(
        "/research/preparations",
        json={
            "query": "Research Acme's technology business in detail",
            "approval_mode": "ask",
            "provider_credential_id": credential.json()["id"],
            "strength": 2,
        },
        headers=current_user,
    )
    assert created.status_code == 202, created.text
    preparation = created.json()["preparation"]
    assert preparation["status"] == "awaiting_input"
    assert len(preparation["plan_data"]["plan_points"]) == 4

    wrong = client.post(
        f"/research/preparations/{preparation['id']}/answers",
        json={"question_id": "not-current", "answer": "example.com"},
        headers=current_user,
    )
    assert wrong.status_code == 409

    answered = client.post(
        f"/research/preparations/{preparation['id']}/answers",
        json={"question_id": "identity", "answer": "https://acme.example"},
        headers=current_user,
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["status"] == "ready"
    assert answered.json()["answers"] == {"identity": "https://acme.example"}
    assert answered.json()["final_brief"]["questions"] == []
