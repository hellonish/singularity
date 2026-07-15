"""Concrete production assembly for a persisted research run."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.credential_crypto import decrypt_secret
from api.logging_config import StepLogger
from api.models import Report, ResearchRun, User
from api.schemas import ReportVersionCreate
from api.services.llm_credentials import get_credential
from api.services.report_context import ingest_report_content
from api.services.report_context_errors import ReportContextError
from api.services.reports import create_version
from api.services.research import RunEventPublisher
from api.storage.factory import get_object_store
from engine.chat.effort import ChatEffort, reasoning_effort_for_strength
from engine.chat.capability_router import sandbox_enabled, trusted_function_enabled
from engine.chat.execution import RoutedChatToolExecutor
from engine.chat.modal_sandbox import ModalSandboxExecutor
from engine.chat.sandbox_workspace import SandboxWorkspaceManager
from engine.entity_resolution import EntityScope, lightweight_chat_scope
from engine.llm.config import LLMRequestConfig
from engine.llm.groq import ProviderError
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
from engine.research_workflow.preparation import ExecutionRequirement, validated_execution_requirements
from engine.research_workflow.runtime import ResearchCancelled, ResearchInfrastructureError
from engine.research_workflow.workflow import ResearchWorkflow
from vector_store.client import VectorStoreClient
from vector_store.models import RetrievalScope

logger = logging.getLogger(__name__)

# Upper bound on how long a single retryable step will wait for a provider's
# advertised backoff. Groq free-tier rate limits clear within seconds; a longer
# advertised delay is capped so one step can't stall the whole run.
_MAX_RETRY_AFTER_SECONDS = 30.0


def _retry_after_seconds(raw: str | None) -> float:
    """Parse a provider Retry-After hint (e.g. ``"9.2925s"``) into bounded seconds.

    Returns ``0.0`` for a missing or unparseable value so the retry proceeds
    immediately rather than failing. The result is clamped to a safe ceiling.
    """
    if not raw:
        return 0.0
    try:
        seconds = float(str(raw).strip().rstrip("s"))
    except (TypeError, ValueError):
        return 0.0
    if seconds <= 0:
        return 0.0
    return min(seconds, _MAX_RETRY_AFTER_SECONDS)


def _ingest_report_or_fail(
    vector_store,
    *,
    user_id: str,
    report_id: str,
    run_id: str,
    version_number: int,
    content: str,
    title: str,
) -> None:
    """Embed the finalized report, or fail the run without marking it ready.

    A ready report whose context was never stored would make a report-linked
    chat answer without it. On a vector-store failure we log the full cause for
    operators and raise ``ReportContextError`` so the run fails and can retry;
    the report stays out of the 'ready' state.
    """
    try:
        ingest_report_content(
            vector_store,
            user_id=user_id,
            report_id=report_id,
            version_number=version_number,
            content=content,
            title=title,
        )
    except Exception as exc:
        logger.error(
            "report context ingestion failed for report=%s run=%s user=%s: %s",
            report_id,
            run_id,
            user_id,
            exc,
            exc_info=True,
        )
        raise ReportContextError() from exc


class ProviderResearchModel:
    """Small non-streaming adapter; the key only exists during each call."""

    def __init__(self, *, provider_name: str, api_key: str, user_id: str, credential_id: str, model_id: str, caps: RunCaps, strength: int = 2, step_logger: StepLogger | None = None) -> None:
        self._api_key = api_key
        self._user_id = user_id
        self._config = LLMRequestConfig(
            provider=provider_name, credential_id=credential_id, model_id=model_id,
            temperature=0.2, max_output_tokens=3_000,
        )
        self._provider = provider_for(provider_name)
        self._strength = strength
        self._step_logger = step_logger

    async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
        effective_output_tokens = research_completion_budget(
            max_output_tokens, self._config.model_id
        )
        try:
            return await self._complete_once(prompt, effective_output_tokens)
        except ProviderError as exc:
            if not exc.retryable:
                raise
            # Honor a rate-limit backoff before retrying so we don't immediately
            # re-trip the same per-minute budget. Groq reports the wait in the
            # Retry-After header; cap it so a hostile value can't stall the run.
            delay = _retry_after_seconds(exc.retry_after_seconds)
            if delay:
                await asyncio.sleep(delay)
            # One retry with a raised budget also covers transient bad JSON and
            # models that overrun a tight completion limit on hidden reasoning.
            retry_output_tokens = min(effective_output_tokens * 2, 8_192)
            return await self._complete_once(prompt, retry_output_tokens)

    async def _complete_once(self, prompt: str, effective_output_tokens: int) -> str:
        if self._step_logger is not None:
            self._step_logger.step(
                "llm_completion",
                phase="start",
                inputs={"prompt": prompt},
                model_id=self._config.model_id,
                max_output_tokens=effective_output_tokens,
            )
        completion = await self._provider.complete(
            api_key=self._api_key,
            config=LLMRequestConfig(
                provider=self._config.provider,
                credential_id=self._config.credential_id,
                model_id=self._config.model_id,
                temperature=self._config.temperature,
                max_output_tokens=effective_output_tokens,
                reasoning_effort=reasoning_effort_for_strength(
                    self._config.model_id, self._strength
                ),
            ),
            message=prompt,
            end_user_id=self._user_id,
            structured_output=StructuredOutputSpec.json_object(),
        )
        if self._step_logger is not None:
            self._step_logger.step(
                "llm_completion",
                phase="end",
                outputs={"content": completion.content},
                model_id=self._config.model_id,
            )
        return completion.content


def _as_log_payload(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dict__"):
        return vars(value)
    return str(value)


class LoggedToolExecutor:
    """Log trusted tool calls without changing the engine's tool contract."""

    def __init__(self, executor: Any, step_logger: StepLogger) -> None:
        self._executor = executor
        self._step_logger = step_logger

    async def execute(self, invocation):
        self._step_logger.step(
            "tool_call",
            phase="start",
            inputs=_as_log_payload(invocation),
            tool_name=invocation.tool_name,
        )
        try:
            result = await self._executor.execute(invocation)
        except Exception as exc:
            self._step_logger.error("tool_call", exc, tool_name=invocation.tool_name)
            raise
        self._step_logger.step(
            "tool_call",
            phase="end",
            outputs=_as_log_payload(result),
            tool_name=invocation.tool_name,
        )
        return result

    async def aclose(self) -> None:
        await self._executor.aclose()

    def sandbox_workspace_states(self) -> list[dict[str, Any]]:
        getter = getattr(self._executor, "sandbox_workspace_states", None)
        return list(getter() if getter is not None else [])

    async def restore_sandbox_workspace_states(self, states: list[dict[str, Any]]) -> None:
        restore = getattr(self._executor, "restore_sandbox_workspace_states", None)
        if restore is not None:
            await restore(states)


async def execute_research_run(*, run: ResearchRun, session: AsyncSession) -> None:
    """Run the same LangGraph workflow used by CLI, with real BYOK and Modal tools."""
    step_log = StepLogger(
        "research",
        user_id=run.user_id,
        run_id=run.id,
        report_id=run.report_id,
    )
    step_log.step(
        "run",
        phase="start",
        inputs={
            "query": run.query,
            "run_data": {
                key: value
                for key, value in run.run_data.items()
                if key != "sandbox_workspaces"
            },
            "restorable_sandbox_count": len(run.run_data.get("sandbox_workspaces") or []),
        },
    )
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
    # Real-inference smoke test: one node, one search, one fetch. The gate is
    # enforced at run creation; run_data carries the resolved flag.
    test_mode = bool(run.run_data.get("test_mode"))
    caps = RunCaps.for_test() if test_mode else RunCaps.for_strength(int(run.run_data.get("strength", 2)))
    step_log.step(
        "runtime_configuration",
        phase="end",
        provider=credential.provider,
        model_id=model_id,
        strength=run.run_data.get("strength", 2),
        test_mode=test_mode,
    )
    search_variants = 1 if test_mode else 3
    research_brief = dict(run.run_data.get("research_brief") or {})
    execution_requirements = [
        ExecutionRequirement.model_validate(item).model_dump(mode="json")
        for item in list(research_brief.get("execution_requirements") or [])
    ]
    if not execution_requirements:
        execution_requirements = [
            item.model_dump(mode="json")
            for item in validated_execution_requirements(
                run.query, list(research_brief.get("plan_points") or [])
            )
        ]
        if execution_requirements:
            research_brief = {
                **research_brief,
                "execution_requirements": execution_requirements,
            }
            run.run_data = {**run.run_data, "research_brief": research_brief}
            await session.commit()
    modal_master = os.getenv("SINGULARITY_MODAL_ENABLED", "0") == "1"
    if not trusted_function_enabled(modal_master):
        raise ValueError("This research run requires the trusted Modal Function tier, but it is disabled")
    if any(item.get("required", True) for item in execution_requirements) and not sandbox_enabled(modal_master):
        raise ValueError("This research run requires Modal Sandbox, but Sandbox execution is disabled")
    entity_scope = EntityScope.model_validate(research_brief.get("entity_scope") or {})
    if not research_brief:
        # Compatibility callers may still create a run directly. They cannot
        # bypass the identity boundary: a zero-call conservative scope is used,
        # and an ambiguous target fails before any web tool is dispatched.
        entity_scope = lightweight_chat_scope(run.query)
        if not entity_scope.resolved:
            raise ValueError(
                "Research target entity is ambiguous. Prepare the run in Ask or Auto mode first."
            )
    model = ProviderResearchModel(
        provider_name=credential.provider,
        api_key=decrypt_secret(credential.encrypted_secret),
        user_id=run.user_id,
        credential_id=credential.id,
        model_id=model_id,
        caps=caps,
        strength=1 if test_mode else int(run.run_data.get("strength", 2)),
        step_logger=step_log,
    )
    scope = RetrievalScope(user_id=run.user_id, report_id=run.report_id, research_run_id=run.id)
    vector_store = VectorStoreClient()
    answerer = LLMAnswerer(model)
    # Resolver nodes run in parallel, but an AsyncSession permits only one
    # database operation at a time. Share this lock with progress persistence.
    session_lock = asyncio.Lock()
    event_publisher = RunEventPublisher(session, run, session_lock=session_lock)

    async def publish_progress(event: dict[str, Any]) -> None:
        step_log.step(
            str(event.get("status") or "progress"),
            phase="progress",
            outputs=event,
            node=event.get("node"),
        )
        await event_publisher.append("research.progress", event)

    async def persist_workspace_states(states: list[dict[str, Any]]) -> None:
        async with session_lock:
            await session.refresh(run)
            run.run_data = {**run.run_data, "sandbox_workspaces": states}
            await session.commit()

    workspace_manager = SandboxWorkspaceManager(state_reporter=persist_workspace_states)
    tool_executor = LoggedToolExecutor(
        RoutedChatToolExecutor(
            sandbox=ModalSandboxExecutor(workspace_manager=workspace_manager)
        ),
        step_log,
    )
    await tool_executor.restore_sandbox_workspace_states(
        list(run.run_data.get("sandbox_workspaces") or [])
    )
    bounded_resolver = BoundedResearchResolver(
        tool_executor,
        answerer,
        max_fetches=caps.max_fetches,
        max_search_variants=search_variants,
        progress_reporter=publish_progress,
        entity_scope=entity_scope,
        execution_requirements=execution_requirements,
        run_id=run.id,
        effort=(
            ChatEffort.MEDIUM
            if int(run.run_data.get("strength", 2)) <= 1
            else ChatEffort.HIGH
            if int(run.run_data.get("strength", 2)) == 2
            else ChatEffort.ULTRA
        ),
    )

    async def resolver(node, max_tool_calls: int) -> dict[str, Any]:
        step_log.step(
            "resolve_node",
            phase="start",
            inputs=node.model_dump(mode="json") if hasattr(node, "model_dump") else str(node),
            node_id=node.node_id,
            max_tool_calls=max_tool_calls,
        )
        async with session_lock:
            await session.refresh(run)
            if run.status == "cancelled" or run.run_data.get("cancellation_requested"):
                raise ResearchCancelled("research run was cancelled")
        result = await bounded_resolver(node, max_tool_calls)
        workspace_states = tool_executor.sandbox_workspace_states()
        if workspace_states:
            async with session_lock:
                await session.refresh(run)
                run.run_data = {**run.run_data, "sandbox_workspaces": workspace_states}
                await session.commit()
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
        # Announce each newly-cited source so the live feed can show a
        # "Source added" line and increment the Sources telemetry counter. This
        # fires only for sources that persisted with a citable URL.
        for source in records:
            await publish_progress({
                "kind": "source_added",
                "phase": "researching",
                "status": "source_added",
                "message": f"Source added — {source['name']}",
                "node_id": node.node_id,
                "title": source["title"],
                "url": source["url"],
                "source_type": source["source_type"],
            })
        step_log.step(
            "resolve_node",
            phase="end",
            outputs=result,
            node_id=node.node_id,
            evidence_count=len(result.get("evidence", [])),
        )
        return result

    cleanup_error: Exception | None = None
    try:
        async with checkpoint_context(settings.database_url) as checkpointer:
            workflow = ResearchWorkflow(
                planner=LLMPlanner(
                    model,
                    max_perspectives=1 if test_mode else min(3, max(2, int(run.run_data.get("strength", 2)) + 1)),
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
                step_log.step(
                    "workflow_node",
                    phase="end",
                    outputs=payload,
                    node=node_name,
                    cycle=payload.get("cycle"),
                )
                await event_publisher.append(
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
                        research_brief=research_brief,
                    )
                )
    finally:
        # The shared executor owns the Modal gRPC client. Closing it on both
        # success and failure prevents the worker from leaking input-plane
        # channels after a timed-out tool call.
        try:
            await tool_executor.aclose()
        except Exception as exc:
            logger.warning("research tool cleanup failed", exc_info=True)
            # Trusted Function client shutdown is best-effort and must not
            # invalidate a completed report. A remaining private Sandbox state,
            # however, means termination failed and its cleanup handle must be
            # retained instead of marking the run complete.
            if tool_executor.sandbox_workspace_states():
                cleanup_error = exc
        if execution_requirements and cleanup_error is None:
            try:
                await publish_progress({
                    "kind": "sandbox",
                    "phase": "researching",
                    "status": "sandbox_closed",
                    "message": "Task-scoped Sandbox workspace closed",
                })
            except Exception:
                logger.warning("research Sandbox close progress could not be persisted", exc_info=True)

    if cleanup_error is not None:
        raise ResearchInfrastructureError(
            "Research completed but its task-scoped Sandbox could not be terminated safely"
        ) from cleanup_error

    report = await session.get(Report, run.report_id)
    if report is None:
        raise ValueError("research run report no longer exists")
    document = state["report"]
    markdown = to_markdown(ResearchDocument.model_validate(document))
    version = await create_version(
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
    # The report is now produced finally: embed it under its {user_id, report_id}
    # scope so a report-linked chat can retrieve it. This is separate from the
    # per-node evidence scope above, which also carries research_run_id.
    _ingest_report_or_fail(
        vector_store,
        user_id=run.user_id,
        report_id=report.id,
        run_id=run.id,
        version_number=version.version_number,
        content=markdown,
        title=report.title or "",
    )
    step_log.step(
        "report_persisted",
        phase="end",
        outputs={"content": markdown},
        version_number=version.version_number,
    )
    report.status = "ready"
    run.status = "completed"
    run.finished_at = datetime.now(timezone.utc)
    retained_run_data = {
        key: value for key, value in run.run_data.items() if key != "sandbox_workspaces"
    }
    run.run_data = {
        **retained_run_data,
        "graph_events": state.get("events", []),
        "qa_reviews": state.get("qa_reviews", []),
        "checkpoint_started": True,
    }
    await session.commit()
    step_log.step("run", phase="end", status=run.status)
