"""Live assembly for the bounded research graph.

Wires the real provider adapter, Modal tool executor, and LLM collaborators
into a :class:`ResearchWorkflow` and returns terminal-ready Markdown. Consumed
by the CLI research mode (``engine.cli.repl``) and the API research runtime.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from inspect import isawaitable
from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import Any

from engine.chat.effort import ChatEffort, reasoning_effort_for_model
from engine.chat.modal_tools import ModalToolExecutor
from engine.llm.config import LLMRequestConfig
from engine.llm.groq import ProviderError
from engine.llm.providers import LLMProvider, provider_for
from engine.llm.structured import StructuredOutputSpec

from .caps import RunCaps, format_runtime_seconds
from .document import ResearchDocument, validate_document
from .agents import (
    LLMAnswerer,
    LLMLead,
    LLMPlanner,
    LLMQA,
    LLMWriter,
    research_completion_budget,
)
from .markdown import to_markdown
from .resolver import BoundedResearchResolver
from .workflow import ResearchWorkflow


class TerminalResearchModel:
    """Step-capped provider adapter whose key is retained only for one CLI run."""

    def __init__(
        self,
        *,
        api_key: str,
        model_id: str,
        caps: RunCaps,
        provider_name: str = "groq",
        provider: LLMProvider | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_id = model_id
        self._provider_name = provider_name
        self._provider = provider or provider_for(provider_name)
        self._step_timeout_seconds = caps.llm_step_timeout_seconds

    async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
        effective_output_tokens = research_completion_budget(
            max_output_tokens, self._model_id
        )
        try:
            return await self._complete_once(prompt, effective_output_tokens)
        except ProviderError as exc:
            if not exc.retryable:
                raise
            # One retry with a raised budget covers both transient bad JSON
            # and models that overrun a tight completion limit on hidden
            # reasoning; the cap keeps the request within common model limits.
            retry_output_tokens = min(effective_output_tokens * 2, 8_192)
            return await self._complete_once(prompt, retry_output_tokens)

    async def _complete_once(self, prompt: str, effective_output_tokens: int) -> str:
        try:
            async with asyncio.timeout(self._step_timeout_seconds):
                completion = await self._provider.complete(
                    api_key=self._api_key,
                    config=LLMRequestConfig(
                        provider=self._provider_name,
                        credential_id="terminal-session",
                        model_id=self._model_id,
                        temperature=0.2,
                        max_output_tokens=effective_output_tokens,
                        # Research steps request compact JSON (some as small as 500
                        # tokens). GPT-OSS can otherwise spend the entire completion
                        # budget on hidden reasoning. The helper returns None for
                        # providers/models that do not support this option.
                        reasoning_effort=reasoning_effort_for_model(
                            self._model_id, ChatEffort.INSTANT
                        ),
                    ),
                    message=prompt,
                    end_user_id="singularity-terminal",
                    structured_output=StructuredOutputSpec.json_object(),
                )
        except TimeoutError as exc:
            raise TimeoutError(
                f"{self._provider_name.title()} model {self._model_id} exceeded the "
                f"{self._step_timeout_seconds}-second research-step limit"
            ) from exc
        return completion.content


async def run_research(
    *,
    query: str,
    strength: int,
    output_dir: Path,
    api_key: str,
    provider_name: str = "groq",
    model_id: str,
    provider: LLMProvider | None = None,
    executor: ModalToolExecutor | None = None,
    on_progress: Callable[[dict[str, Any]], Awaitable[None] | None] | None = None,
) -> str:
    """Run real provider-and-Modal research and return terminal-ready Markdown."""
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    diagnostics_path = output_dir / "latest-research-diagnostics.jsonl"

    def record(event: dict[str, Any]) -> None:
        safe = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            **event,
        }
        with diagnostics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(safe, ensure_ascii=False, default=str) + "\n")

    diagnostics_path.write_text("", encoding="utf-8")
    async def report_progress(event: dict[str, Any]) -> None:
        record(event)
        if on_progress is not None:
            result = on_progress(event)
            if isawaitable(result):
                await result

    caps = RunCaps.for_strength(strength)
    record({
        "phase": "run",
        "status": "started",
        "provider": provider_name,
        "model": model_id,
        "strength": strength,
        "llm_step_timeout_seconds": caps.llm_step_timeout_seconds,
        "max_runtime_seconds": caps.max_runtime_seconds,
        "max_nodes": caps.max_nodes,
        "qa_cycles": caps.qa_cycles,
    })
    model = TerminalResearchModel(
        api_key=api_key,
        provider_name=provider_name,
        model_id=model_id,
        caps=caps,
        provider=provider,
    )
    answerer = LLMAnswerer(model, caps)
    owns_executor = executor is None
    tool_executor = executor or ModalToolExecutor()
    resolver = BoundedResearchResolver(
        tool_executor,
        answerer,
        max_fetches=caps.max_fetches,
        progress_reporter=report_progress,
    )

    async def persistable_resolver(node, max_tool_calls: int) -> dict[str, Any]:
        result = await resolver(node, max_tool_calls)
        source_records: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for evidence in result.get("evidence", []):
            url = str(evidence.get("url", ""))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            source_records.append({
                "tag": "S" + hashlib.sha256(url.encode()).hexdigest()[:10],
                "name": str(evidence.get("title") or url)[:120],
                "title": str(evidence.get("title") or url),
                "url": url,
                "source_type": str(evidence.get("source_type") or "web"),
                "date": evidence.get("date"),
            })
        result["source_records"] = source_records
        result["evidence_ids"] = [record["tag"] for record in source_records]
        return result

    workflow = ResearchWorkflow(
        # Every depth performs model-driven objective clarification and query
        # decomposition. Strength controls how many independent perspectives
        # and plan nodes survive the bounded merge; it no longer disables
        # planning for Quick research.
        planner=LLMPlanner(model, max_perspectives=strength),
        lead=LLMLead(),
        resolver=persistable_resolver,
        qa_reviewer=LLMQA(model),
        writer=LLMWriter(model),
    )
    try:
        async with asyncio.timeout(caps.max_runtime_seconds):
            state = await workflow.run(
                run_id=run_id,
                query=query,
                caps=caps,
                on_progress=report_progress,
            )
        record({"phase": "run", "status": "completed"})
    except TimeoutError as exc:
        message = f"Research run reached its {format_runtime_seconds(caps.max_runtime_seconds)} deadline"
        record({
            "phase": "run",
            "status": "failed",
            "error_type": "TimeoutError",
            "message": message,
        })
        raise TimeoutError(message) from exc
    except Exception as exc:
        record({
            "phase": "run",
            "status": "failed",
            "error_type": type(exc).__name__,
            "provider_code": getattr(exc, "code", None),
            "message": str(exc)[:500],
        })
        raise
    finally:
        if owns_executor:
            await tool_executor.aclose()
    document = validate_document(ResearchDocument.model_validate(state["report"]))
    return to_markdown(document)
