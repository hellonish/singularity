"""Concrete production assembly for a persisted research run."""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.credential_crypto import decrypt_secret
from api.models import Report, ResearchRun, User
from api.schemas import ReportVersionCreate
from api.services.llm_credentials import get_credential
from api.services.reports import create_version
from api.services.research import append_event
from api.storage.factory import get_object_store
from engine.chat.effort import ChatEffort, reasoning_effort_for_model
from engine.chat.modal_tools import ModalToolExecutor
from engine.llm.config import LLMRequestConfig
from engine.llm.structured import StructuredOutputSpec
from engine.llm import provider_for
from engine.research_workflow.caps import RunCaps
from engine.research_workflow.checkpoint import checkpoint_context
from engine.research_workflow.evidence import persist_evidence
from engine.research_workflow.agents import (
    LLMAnswerer,
    LLMLead,
    LLMPlanner,
    LLMQA,
    LLMWriter,
    research_completion_budget,
)
from engine.research_workflow.markdown import to_markdown
from engine.research_workflow.document import ResearchDocument
from engine.research_workflow.resolver import BoundedResearchResolver
from engine.research_workflow.runtime import ResearchCancelled
from engine.research_workflow.workflow import ResearchWorkflow
from vector_store.client import VectorStoreClient
from vector_store.models import RetrievalScope


class ProviderResearchModel:
    """Small non-streaming adapter; the key only exists during each call."""

    def __init__(self, *, provider_name: str, api_key: str, user_id: str, credential_id: str, model_id: str, caps: RunCaps) -> None:
        self._api_key = api_key
        self._user_id = user_id
        self._config = LLMRequestConfig(
            provider=provider_name, credential_id=credential_id, model_id=model_id,
            temperature=0.2, max_output_tokens=3_000,
        )
        self._provider = provider_for(provider_name)

    async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
        effective_output_tokens = research_completion_budget(
            max_output_tokens, self._config.model_id
        )
        completion = await self._provider.complete(
            api_key=self._api_key,
            config=LLMRequestConfig(
                provider=self._config.provider,
                credential_id=self._config.credential_id,
                model_id=self._config.model_id,
                temperature=self._config.temperature,
                max_output_tokens=effective_output_tokens,
                reasoning_effort=reasoning_effort_for_model(
                    self._config.model_id, ChatEffort.INSTANT
                ),
            ),
            message=prompt,
            end_user_id=self._user_id,
            structured_output=StructuredOutputSpec.json_object(),
        )
        return completion.content


async def execute_research_run(*, run: ResearchRun, session: AsyncSession) -> None:
    """Run the same LangGraph workflow used by CLI, with real BYOK and Modal tools."""
    credential_id = str(run.run_data.get("provider_credential_id") or "")
    if not credential_id:
        raise ValueError("research run requires provider_credential_id")
    credential = await get_credential(session, run.user_id, credential_id)
    fallback = {
        "groq": settings.groq_fallback_model,
        "deepseek": settings.deepseek_fallback_model,
        "openrouter": settings.openrouter_fallback_model,
    }[credential.provider]
    model_id = str(run.run_data.get("model_id") or credential.default_model_id or fallback)
    caps = RunCaps.for_strength(int(run.run_data.get("strength", 2)))
    model = ProviderResearchModel(
        provider_name=credential.provider,
        api_key=decrypt_secret(credential.encrypted_secret),
        user_id=run.user_id,
        credential_id=credential.id,
        model_id=model_id,
        caps=caps,
    )
    scope = RetrievalScope(user_id=run.user_id, report_id=run.report_id, research_run_id=run.id)
    vector_store = VectorStoreClient()
    answerer = LLMAnswerer(model)

    async def publish_progress(event: dict[str, Any]) -> None:
        await append_event(session, run, "research.progress", event)

    bounded_resolver = BoundedResearchResolver(
        ModalToolExecutor(),
        answerer,
        max_fetches=caps.max_fetches,
        progress_reporter=publish_progress,
    )

    async def resolver(node, max_tool_calls: int) -> dict[str, Any]:
        await session.refresh(run)
        if run.status == "cancelled":
            raise ResearchCancelled("research run was cancelled")
        result = await bounded_resolver(node, max_tool_calls)
        persistence = persist_evidence(
            vector_store=vector_store,
            scope=scope,
            node_id=node.node_id,
            evidence=result.get("evidence", []),
            answer=result,
        )
        records = []
        for source in persistence["source_records"]:
            source_id = str(source["document_id"])
            url = str(source["url"] or "")
            if not url:
                continue
            records.append({
                "tag": "S" + hashlib.sha256(source_id.encode()).hexdigest()[:10],
                "name": str(source["title"] or url)[:120],
                "title": str(source["title"] or url),
                "url": url,
                "source_type": str(source["source_type"] or "web"),
                "date": source.get("date"),
                "document_id": source_id,
            })
        result["evidence_ids"] = persistence["source_ids"]
        result["source_records"] = records
        return result

    async with checkpoint_context(settings.database_url) as checkpointer:
        workflow = ResearchWorkflow(
            planner=LLMPlanner(
                model,
                max_perspectives=min(3, max(2, int(run.run_data.get("strength", 2)) + 1)),
            ),
            lead=LLMLead(),
            resolver=resolver,
            qa_reviewer=LLMQA(model),
            writer=LLMWriter(model),
            checkpointer=checkpointer,
        )
        resuming = bool(run.run_data.get("checkpoint_started"))
        if not resuming:
            run.run_data = {**run.run_data, "checkpoint_started": True}
            await session.commit()
        async def publish(node_name: str, payload: dict[str, Any]) -> None:
            await append_event(
                session,
                run,
                "research.phase",
                {"node": node_name, "details": payload.get("events", []), "cycle": payload.get("cycle")},
            )

        # ARQ's job timeout protects the worker process; this smaller,
        # strength-specific deadline is the user-visible research budget.
        async with asyncio.timeout(caps.max_runtime_seconds):
            state = await (
                workflow.resume(run_id=run.id)
                if resuming
                else workflow.run(
                    run_id=run.id,
                    query=run.query,
                    caps=caps,
                    on_update=publish,
                    on_progress=publish_progress,
                )
            )

    report = await session.get(Report, run.report_id)
    if report is None:
        raise ValueError("research run report no longer exists")
    document = state["report"]
    markdown = to_markdown(ResearchDocument.model_validate(document))
    await create_version(
        session,
        report,
        ReportVersionCreate(
            content=markdown,
            content_format="markdown",
            change_note="Generated by bounded LangGraph research workflow",
            version_data={"research_document": document, "run_id": run.id},
        ),
        get_object_store(),
    )
    report.status = "ready"
    run.status = "completed"
    run.finished_at = datetime.now(timezone.utc)
    run.run_data = {
        **run.run_data,
        "graph_events": state.get("events", []),
        "qa_reviews": state.get("qa_reviews", []),
        "checkpoint_started": True,
    }
    await session.commit()
