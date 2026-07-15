"""Request-scoped assembly for Research Ask and Auto preparation modes."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.credential_crypto import decrypt_secret
from api.models import ResearchPreparation, ResearchRun, User
from api.schemas import ResearchPreparationCreate
from api.services import research as research_service
from api.services.llm_credentials import get_credential
from engine.chat.effort import ChatEffort, reasoning_effort_for_strength
from engine.chat.modal_tools import ModalToolExecutor
from engine.entity_resolution import EntityRef, EntityResolutionStatus
from engine.llm import provider_for
from engine.llm.config import LLMRequestConfig
from engine.llm.structured import StructuredOutputSpec
from engine.research_workflow.preparation import (
    ClarificationQuestion,
    ResearchBrief,
    ensure_ask_question,
    final_brief_prompt,
    initial_brief_prompt,
    parse_brief,
)
from engine.tools.contracts import ChatToolInvocation


class PreparationModel:
    def __init__(
        self,
        *,
        provider_name: str,
        api_key: str,
        credential_id: str,
        model_id: str,
        user_id: str,
        strength: int,
    ) -> None:
        self._provider = provider_for(provider_name)
        self._api_key = api_key
        self._user_id = user_id
        self._strength = strength
        self._config = LLMRequestConfig(
            provider=provider_name,
            credential_id=credential_id,
            model_id=model_id,
            temperature=0.1,
            max_output_tokens=2_500,
            reasoning_effort=reasoning_effort_for_strength(model_id, strength),
        )

    async def complete(self, prompt: str, *, max_output_tokens: int = 2_500) -> str:
        completion = await self._provider.complete(
            api_key=self._api_key,
            config=LLMRequestConfig(
                provider=self._config.provider,
                credential_id=self._config.credential_id,
                model_id=self._config.model_id,
                temperature=self._config.temperature,
                max_output_tokens=max_output_tokens,
                reasoning_effort=self._config.reasoning_effort,
            ),
            message=prompt,
            end_user_id=self._user_id,
            structured_output=StructuredOutputSpec.json_object(),
        )
        return completion.content


async def _model_for(
    session: AsyncSession, user: User, preparation: ResearchPreparation
) -> PreparationModel:
    credential = await get_credential(session, user.id, preparation.provider_credential_id)
    fallback = {
        "groq": settings.groq_fallback_model,
        "deepseek": settings.deepseek_fallback_model,
        "openrouter": settings.openrouter_fallback_model,
    }[credential.provider]
    model_id = preparation.model_id or credential.default_model_id or fallback
    preparation.model_id = model_id
    await session.commit()
    return PreparationModel(
        provider_name=credential.provider,
        api_key=decrypt_secret(credential.encrypted_secret),
        credential_id=credential.id,
        model_id=model_id,
        user_id=user.id,
        strength=preparation.strength,
    )


async def _entity_discovery(preparation: ResearchPreparation) -> list[dict[str, Any]]:
    executor = ModalToolExecutor()
    try:
        result = await executor.execute(
            ChatToolInvocation(
                run_id=preparation.id,
                skill_id="source_discovery",
                tool_name="web_search",
                query=preparation.query,
                arguments={"max_results": 8},
                effort=ChatEffort.MEDIUM,
                timeout_seconds=60.0,
            )
        )
    finally:
        await executor.aclose()
    if result.error:
        raise RuntimeError(f"Entity discovery failed: {result.error}")
    return list(result.sources or [])[:8]


async def create_preparation(
    session: AsyncSession, user: User, body: ResearchPreparationCreate
) -> tuple[ResearchPreparation, ResearchRun | None]:
    preparation = await research_service.create_preparation(session, user, body)
    try:
        model = await _model_for(session, user, preparation)
        draft = parse_brief(
            await model.complete(
                initial_brief_prompt(query=preparation.query, approval_mode=preparation.approval_mode)
            )
        )
        if preparation.approval_mode == "ask":
            draft = ensure_ask_question(draft)
            await research_service.store_preparation_brief(
                session, preparation, plan_data=draft.model_dump(mode="json"), final=False
            )
            return preparation, None

        candidates = (
            await _entity_discovery(preparation)
            if draft.entity_scope.status == EntityResolutionStatus.AMBIGUOUS
            else []
        )
        final = parse_brief(
            await model.complete(
                final_brief_prompt(
                    query=preparation.query,
                    draft=draft,
                    answers={},
                    approval_mode="auto",
                    discovery_sources=candidates,
                )
            )
        )
        if final.entity_scope.status == EntityResolutionStatus.AMBIGUOUS:
            selected_entities = final.entity_scope.entities or draft.entity_scope.entities
            if not selected_entities and candidates:
                candidate = candidates[0]
                candidate_name = str(candidate.get("title") or candidate.get("url") or "Selected entity")[:240]
                selected_entities = [EntityRef(
                    entity_id="auto_selected_1",
                    mention=candidate_name,
                    canonical_name=candidate_name,
                    identifiers=[str(candidate.get("url") or "")],
                    selected_description=str(candidate.get("snippet") or "")[:600],
                    confidence=0.35,
                )]
            if not selected_entities:
                raise ValueError("Auto mode could not find an entity candidate to select")
            final = final.model_copy(update={
                "entity_scope": final.entity_scope.model_copy(update={
                    "status": EntityResolutionStatus.RESOLVED,
                    "entities": selected_entities,
                    "assumptions": [
                        *final.entity_scope.assumptions,
                        "Auto mode selected the highest-context entity candidate; verify the recorded identity if needed.",
                    ],
                }),
                "assumptions": [
                    *final.assumptions,
                    "Auto mode proceeded with the highest-context entity candidate.",
                ],
            })
        final = final.model_copy(update={"questions": []})
        await research_service.store_preparation_brief(
            session,
            preparation,
            plan_data={
                **final.model_dump(mode="json"),
                "entity_discovery_candidates": candidates,
            },
            final=True,
        )
        run = await research_service.start_preparation(session, user, preparation)
        return preparation, run
    except Exception:
        await research_service.fail_preparation(
            session, preparation, "Research preparation could not resolve the request. Please try again."
        )
        raise


async def finalize_after_answers(
    session: AsyncSession, user: User, preparation: ResearchPreparation
) -> ResearchPreparation:
    model = await _model_for(session, user, preparation)
    draft = ResearchBrief.model_validate(preparation.plan_data)
    final = parse_brief(
        await model.complete(
            final_brief_prompt(
                query=preparation.query,
                draft=draft,
                answers={str(key): str(value) for key, value in preparation.answers.items()},
                approval_mode="ask",
            )
        )
    )
    final = final.model_copy(update={"questions": []})
    if final.entity_scope.status == EntityResolutionStatus.AMBIGUOUS:
        questions = list(preparation.plan_data.get("questions", []))
        if len(questions) < 4:
            mention = final.entity_scope.entities[0].mention if final.entity_scope.entities else "the target entity"
            questions.append(ClarificationQuestion(
                question_id=f"entity_resolution_{len(questions) + 1}",
                text=f"What exact {mention} should I research? Add its official site, ticker, location, role, or full legal name.",
                reason="The earlier details still match more than one real-world entity.",
            ).model_dump(mode="json"))
            preparation.plan_data = {**preparation.plan_data, "questions": questions}
            preparation.status = "awaiting_input"
            await session.commit()
            await session.refresh(preparation)
            return preparation
        await research_service.fail_preparation(
            session,
            preparation,
            "The target entity is still ambiguous after four clarification questions.",
        )
        raise ValueError("The target entity is still ambiguous; refine the research prompt and try again")
    return await research_service.store_preparation_brief(
        session, preparation, plan_data=final.model_dump(mode="json"), final=True
    )
