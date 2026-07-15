from __future__ import annotations

import asyncio
import json
import re
import time
from inspect import isawaitable
from collections.abc import Awaitable, Callable
from typing import Any

from engine.chat.effort import ChatEffort, get_chat_effort_profile
from engine.entity_resolution import (
    EntityScope,
    SourceEntityDecision,
    classify_source,
    scope_search_query,
)
from engine.research_workflow.skill_router import select_skills
from engine.tools import TOOL_REGISTRY
from engine.tools.contracts import TOOL_ARGUMENT_MODELS, ChatToolInvocation

# Discovery tools whose argument model has no required field beyond the standard
# free-text ``query`` — these can be dispatched by a deterministic router. Tools
# with a required argument (e.g. web_fetch needs ``url``) are excluded.
TOOL_ARGUMENT_QUERY_TOOLS = frozenset(
    tool_name
    for tool_name, model in TOOL_ARGUMENT_MODELS.items()
    if not any(field.is_required() for field in model.model_fields.values())
)

from .caps import RunCaps
from .dag import ResearchNode
from .evidence import rank_evidence
from .runtime import ResearchInfrastructureError


Answerer = Callable[[ResearchNode, list[dict[str, Any]]], Awaitable[dict[str, Any]]]

# How many times a single Modal dispatch is retried on an infrastructure-level
# error (channel drop, timeout, remote raise) before we treat the backend as
# down. These retries are transparent to the per-node research budget: they
# re-attempt the *same* logical call rather than spending a new one.
_MODAL_DISPATCH_ATTEMPTS = 3

# Discovery tools are trusted-function search tools that take a free-text
# ``query`` and return sources. A node routes to at most this many domain tools
# (beyond the general web search) so its call budget still leaves room to fetch.
_MAX_DOMAIN_DISCOVERY_TOOLS = 2

# Web tools are the general-purpose fallback that always applies. Everything
# else surfaced by the skill router is a domain-specific discovery tool the node
# should prefer when the question matches (pubmed, sec_edgar, arxiv, …).
_GENERAL_WEB_TOOLS = {"web_search", "web_fetch", "browser_render"}
# Redact credential-like tokens from tool output before it reaches an LLM
# prompt, mirroring the chat tool loop's ``_redact_result``.
_CREDENTIAL_PATTERN = re.compile(
    r"(?i)(api[_-]?key|apikey|token|authorization)(=|:|%3d)\s*([^&\s'\"]+)"
)


def domain_discovery_tools(question: str, *, limit: int = _MAX_DOMAIN_DISCOVERY_TOOLS) -> list[tuple[str, str]]:
    """Deterministically route a node question to domain discovery tools.

    Reuses the chat skill router (``select_skills``) to shortlist skills, then
    keeps their registered *discovery* tools — trusted-function search tools that
    take a free-text query — excluding the general web tools (which always run as
    the fallback). Returns ``(skill_id, tool_name)`` pairs in shortlist order.
    """
    selected = select_skills(question)
    routed: list[tuple[str, str]] = []
    seen: set[str] = set()
    for skill_id in selected.ids:
        from engine.skills import SKILL_REGISTRY

        try:
            tools = SKILL_REGISTRY.get(skill_id).config.tools
        except KeyError:
            continue
        for tool_name in tools:
            if tool_name in _GENERAL_WEB_TOOLS or tool_name in seen:
                continue
            try:
                descriptor = TOOL_REGISTRY.descriptor(tool_name)
            except KeyError:
                continue
            # Only trusted-function search tools take a free-text query; sandbox
            # tools (code_execution, dataset_analysis) need structured inputs a
            # deterministic router cannot synthesise, so skip them here.
            if descriptor.execution_kind != "trusted_function":
                continue
            if tool_name not in TOOL_ARGUMENT_QUERY_TOOLS:
                continue
            seen.add(tool_name)
            routed.append((skill_id, tool_name))
            if len(routed) >= limit:
                return routed
    return routed


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return _CREDENTIAL_PATTERN.sub(r"\1\2[REDACTED]", value)
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    return value


class BoundedResearchResolver:
    """Search/fetch resolver with an enforced four-invocation budget.

    The executor may be the deployed Modal trusted-function adapter or a local
    test double. Credentials remain outside this class and are never included
    in a tool invocation.
    """

    def __init__(self, executor, answerer: Answerer, *, timeout_seconds: int | None = None, max_fetches: int = 2, max_search_variants: int = 3, progress_reporter=None, entity_scope: EntityScope | dict[str, Any] | None = None, execution_requirements: list[dict[str, Any]] | None = None, run_id: str | None = None, effort: ChatEffort = ChatEffort.MEDIUM):
        self.executor = executor
        self.answerer = answerer
        self.timeout_seconds = timeout_seconds or get_chat_effort_profile(effort).timeout_seconds
        self.max_fetches = max(0, min(max_fetches, RunCaps.MAX_FETCHES_CEILING))
        # How many reformulation attempts web_search may make. Production uses
        # the full set; test mode sets this to 1 so a run makes exactly one
        # real search call.
        self.max_search_variants = max(1, min(max_search_variants, 3))
        self.progress_reporter = progress_reporter
        self.entity_scope = EntityScope.model_validate(entity_scope or {})
        self.execution_requirements = list(execution_requirements or [])
        self.run_id = run_id
        self.effort = effort
        self._sandbox_announced: set[str] = set()
        self._sandbox_workspace_ids: dict[str, str] = {}
        self._sandbox_call_tasks: dict[str, asyncio.Task[Any]] = {}
        self._sandbox_call_lock = asyncio.Lock()

    # Resolver statuses that describe a single tool invocation's lifecycle. The
    # UI renders these as a tool chip / web_search card; the remaining statuses
    # (node_started, node_completed, source_unavailable) describe the node and
    # default to the generic "phase" kind.
    _TOOL_CALL_STATUSES = frozenset({
        "tool_dispatched", "tool_routed", "tool_reformulating",
        "tool_completed", "tool_failed", "tool_retry",
    })

    async def _progress(self, **event: Any) -> None:
        if self.progress_reporter is not None:
            # Stamp a stable ``kind`` so the frontend can route each event to one
            # component. Tool-lifecycle statuses become "tool_call"; everything
            # else is a node-level "phase" event.
            event.setdefault(
                "kind",
                (
                    "sandbox"
                    if str(event.get("status") or "").startswith("sandbox_")
                    else "tool_call" if event.get("status") in self._TOOL_CALL_STATUSES else "phase"
                ),
            )
            result = self.progress_reporter(event)
            if isawaitable(result):
                await result

    async def __call__(self, node: ResearchNode, max_tool_calls: int = 4) -> dict[str, Any]:
        if not 1 <= max_tool_calls <= RunCaps.MAX_TOOL_CALLS_CEILING:
            raise ValueError(
                f"research node resolver budget must be between 1 and {RunCaps.MAX_TOOL_CALLS_CEILING}"
            )
        calls = 0
        evidence: list[dict[str, Any]] = []
        scoped_question = scope_search_query(node.question, self.entity_scope)
        await self._progress(phase="researching", status="node_started", message=f"Researching: {node.question}", node_id=node.node_id)

        async def admit(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
            admitted: list[dict[str, Any]] = []
            for record in records:
                if record.get("source_type") == "sandbox_execution":
                    record["entity_match"] = {
                        "decision": "aligned",
                        "reason": "Execution used the server-validated input frozen in the approved brief.",
                    }
                    admitted.append(record)
                    continue
                verdict = classify_source(record, self.entity_scope)
                if verdict.decision == SourceEntityDecision.ALIGNED:
                    record["entity_match"] = verdict.model_dump(mode="json")
                    admitted.append(record)
                    continue
                if (
                    self.entity_scope.resolution_mode == "auto"
                    and verdict.decision == SourceEntityDecision.UNCERTAIN
                ):
                    # Auto mode may recover mid-research when a source names the
                    # approved entity but omits the frozen discriminator. Keep
                    # the lower-confidence verdict attached for QA; never admit
                    # a source with no match to the approved entity at all.
                    record["entity_match"] = verdict.model_dump(mode="json")
                    record["entity_match"]["auto_resolved"] = True
                    admitted.append(record)
                    await self._progress(
                        phase="researching",
                        status="source_entity_auto_resolved",
                        message="Auto mode accepted a lower-confidence match to the approved entity",
                        node_id=node.node_id,
                        url=str(record.get("url") or ""),
                        reason=verdict.reason,
                    )
                    continue
                await self._progress(
                    phase="researching",
                    status="source_entity_rejected",
                    message="Rejected a source that did not match the target entity",
                    node_id=node.node_id,
                    url=str(record.get("url") or ""),
                    reason=verdict.reason,
                )
            return admitted

        async def invoke(tool_name: str, query: str, arguments: dict[str, Any], *, skill_id: str = "general_web_research") -> Any:
            """Dispatch one logical tool call, retrying transparently on
            infrastructure errors. Consumes exactly one unit of the research
            budget regardless of how many Modal-level retries it takes.

            Raises ResearchInfrastructureError if the Modal backend stays
            unreachable after every attempt. A failed search is run-fatal;
            a failed individual page fetch is handled below as a source-level
            failure because the rest of the evidence may still be usable.
            """
            is_sandbox = TOOL_REGISTRY.descriptor(tool_name).execution_kind == "sandbox"
            cache_key = (
                json.dumps(
                    {"tool_name": tool_name, "skill_id": skill_id, "arguments": arguments},
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
                if is_sandbox
                else None
            )

            async def dispatch() -> Any:
                nonlocal calls
                if calls >= max_tool_calls:
                    raise RuntimeError("research node tool-call cap exhausted")
                calls += 1
                invocation = ChatToolInvocation(
                    run_id=f"research-run:{self.run_id}" if self.run_id else f"research-node:{node.node_id}",
                    skill_id=skill_id,
                    tool_name=tool_name,
                    query=query,
                    arguments=arguments,
                    effort=self.effort,
                    timeout_seconds=self.timeout_seconds,
                )
                if not is_sandbox:
                    await self._progress(phase="researching", status="tool_dispatched", message=f"Requesting Modal worker for {tool_name}", node_id=node.node_id, tool_name=tool_name)
                started = time.monotonic()
                last_exc: Exception | None = None
                dispatch_attempts = 1 if is_sandbox else _MODAL_DISPATCH_ATTEMPTS
                for attempt in range(dispatch_attempts):
                    try:
                        result = await self.executor.execute(invocation)
                        error = getattr(result, "error", None)
                        sources = list(getattr(result, "sources", []) or [])
                        if not is_sandbox:
                            await self._progress(
                                phase="researching",
                                status="tool_completed" if not error else "tool_failed",
                                message=f"{tool_name} completed" if not error else f"{tool_name} returned an error",
                                node_id=node.node_id, tool_name=tool_name,
                                elapsed_seconds=time.monotonic() - started, source_count=len(sources),
                            )
                        return result
                    except Exception as exc:
                        last_exc = exc
                        if attempt < dispatch_attempts - 1:
                            await self._progress(phase="researching", status="tool_retry", message=f"{tool_name} unreachable — retrying ({attempt + 1}/{dispatch_attempts - 1})", node_id=node.node_id, tool_name=tool_name, error=type(exc).__name__)
                            await asyncio.sleep(2 ** attempt)
                # Every dispatch attempt failed: the backend, not the query, is
                # the problem. Required Sandbox calls are intentionally not
                # replayed after a transport failure because they may mutate.
                await self._progress(
                    phase="researching",
                    status="sandbox_failed" if is_sandbox else "tool_failed",
                    message=f"{tool_name} failed",
                    node_id=node.node_id,
                    tool_name=tool_name,
                    elapsed_seconds=time.monotonic() - started,
                    error=type(last_exc).__name__ if last_exc else "unknown",
                )
                raise ResearchInfrastructureError(
                    f"{tool_name} dispatch failed after {dispatch_attempts} attempts: {last_exc}"
                ) from last_exc

            if cache_key is None:
                return await dispatch()
            async with self._sandbox_call_lock:
                task = self._sandbox_call_tasks.get(cache_key)
                if task is None:
                    task = asyncio.create_task(dispatch())
                    self._sandbox_call_tasks[cache_key] = task
            return await task

        async def search_with_adaptation() -> Any:
            """Run web_search, reformulating the query when it comes back empty
            or errored, until the search succeeds or the call budget is spent.

            A Modal outage propagates as ResearchInfrastructureError from
            invoke(); an empty/errored *result* is a soft failure the agent
            adapts around with a reworded query.
            """
            variants = [
                (scoped_question, {"max_results": 8}),
                (f"{scoped_question} primary source", {"max_results": 5}),
                (f"{scoped_question} report OR study OR data", {"max_results": 5}),
            ][: self.max_search_variants]
            last_result = None
            for query, arguments in variants:
                if calls >= max_tool_calls:
                    break
                result = await invoke("web_search", query, arguments)
                last_result = result
                error = getattr(result, "error", None)
                sources = list(getattr(result, "sources", []) or [])
                if sources and not error:
                    return result
                # Soft failure: the backend answered but the query yielded
                # nothing usable. Signal the reformulation and try the next
                # variant (budget permitting).
                if calls < max_tool_calls:
                    await self._progress(
                        phase="researching", status="tool_reformulating",
                        message="web_search returned no usable results — reformulating",
                        node_id=node.node_id, tool_name="web_search",
                        error=str(error)[:200] if error else None,
                    )
            return last_result

        async def route_domain_tools() -> list[dict[str, Any]]:
            """Dispatch the node's shortlisted domain discovery tools.

            Reserves at least one call for the general web fallback and one for a
            fetch, so domain routing never starves the guaranteed web pass. A
            domain tool that errors or returns nothing is a soft failure: we skip
            it and fall through to web search. Only a full-backend outage
            (ResearchInfrastructureError) is fatal, and that is raised by invoke.
            """
            collected: list[dict[str, Any]] = []
            reserve = 2  # one web_search + one fetch remain available
            for skill_id, tool_name in domain_discovery_tools(node.question):
                if calls >= max_tool_calls - reserve:
                    break
                await self._progress(
                    phase="researching", status="tool_routed",
                    message=f"Routing to domain tool {tool_name}",
                    node_id=node.node_id, tool_name=tool_name,
                )
                result = await invoke(tool_name, scoped_question, {"max_results": 8}, skill_id=skill_id)
                if getattr(result, "error", None):
                    continue
                records = await admit(_evidence_from_result(result, scoped_question))
                if records:
                    collected.extend(records)
            return collected

        async def route_sandbox_tools() -> list[dict[str, Any]]:
            """Run validated execution requirements before web discovery.

            Repository resources come only from the server-frozen brief. A
            required Sandbox failure is run-fatal so web snippets can never be
            substituted for repository inspection.
            """
            collected: list[dict[str, Any]] = []
            for requirement in self.execution_requirements:
                if calls >= max_tool_calls - 1:
                    break
                kind = str(requirement.get("kind") or "")
                if kind in {"code", "dataset"}:
                    validated_arguments = dict(requirement.get("validated_arguments") or {})
                    if not validated_arguments:
                        if requirement.get("required", True):
                            raise ResearchInfrastructureError(
                                f"Required {kind} execution has no validated inline input"
                            )
                        continue
                    tool_name = "code_execution" if kind == "code" else "dataset_analysis"
                    skill_id = tool_name
                    announcement_key = str(requirement.get("resource_reference") or tool_name)
                    if announcement_key not in self._sandbox_announced:
                        self._sandbox_announced.add(announcement_key)
                        await self._progress(
                            phase="researching", status="sandbox_created",
                            message=f"Creating task-scoped {kind} Sandbox",
                            node_id=node.node_id, tool_name=tool_name,
                            profile=requirement.get("profile"),
                        )
                        await self._progress(
                            phase="researching", status="sandbox_ready",
                            message=f"{kind.title()} Sandbox ready",
                            node_id=node.node_id, tool_name=tool_name,
                            profile=requirement.get("profile"),
                        )
                    await self._progress(
                        phase="researching", status="sandbox_command_started",
                        message=f"Running approved {kind} computation",
                        node_id=node.node_id, tool_name=tool_name,
                        profile=requirement.get("profile"),
                        safe_command_label=tool_name,
                    )
                    result = await invoke(
                        tool_name, scoped_question, validated_arguments, skill_id=skill_id
                    )
                    if getattr(result, "error", None):
                        await self._progress(
                            phase="researching", status="sandbox_failed",
                            message=f"Required {kind} execution failed",
                            node_id=node.node_id, tool_name=tool_name,
                            profile=requirement.get("profile"),
                        )
                        raise ResearchInfrastructureError(str(result.error))
                    details = _command_result_details(getattr(result, "content", ""))
                    await self._progress(
                        phase="researching", status="sandbox_command_completed",
                        message=f"{kind.title()} execution evidence collected",
                        node_id=node.node_id, tool_name=tool_name,
                        profile=requirement.get("profile"),
                        **details,
                    )
                    collected.extend(await admit(_evidence_from_result(result, scoped_question)))
                    continue
                if kind == "gpu":
                    validated_arguments = dict(requirement.get("validated_arguments") or {})
                    if not validated_arguments:
                        raise ResearchInfrastructureError(
                            "Required GPU execution has no validated inline code input"
                        )
                    resource_key = str(requirement.get("resource_reference") or "gpu")
                    workspace_id = self._sandbox_workspace_ids.get(resource_key)
                    required_calls = 2 if workspace_id else 3
                    if max_tool_calls - calls < required_calls:
                        raise ResearchInfrastructureError(
                            "The research effort budget is too small for required GPU setup and execution"
                        )
                    if workspace_id is None:
                        await self._progress(
                            phase="researching", status="sandbox_created",
                            message="Creating task-scoped GPU Sandbox",
                            node_id=node.node_id, tool_name="sandbox_create", profile="gpu",
                        )
                        created = await invoke(
                            "sandbox_create", scoped_question,
                            {"purpose": "gpu", "profile": "gpu"},
                            skill_id="sandbox_workspace",
                        )
                        if getattr(created, "error", None):
                            raise ResearchInfrastructureError(str(created.error))
                        try:
                            workspace_id = str(json.loads(created.content)["workspace_id"])
                        except (KeyError, TypeError, ValueError) as exc:
                            raise ResearchInfrastructureError("GPU Sandbox did not return a workspace") from exc
                        self._sandbox_workspace_ids[resource_key] = workspace_id
                        await self._progress(
                            phase="researching", status="sandbox_ready",
                            message="GPU Sandbox ready",
                            node_id=node.node_id, tool_name="sandbox_create", profile="gpu",
                        )
                    written = await invoke(
                        "sandbox_write", scoped_question,
                        {"workspace_id": workspace_id, "files": validated_arguments["files"]},
                        skill_id="sandbox_workspace",
                    )
                    if getattr(written, "error", None):
                        raise ResearchInfrastructureError(str(written.error))
                    await self._progress(
                        phase="researching", status="sandbox_command_started",
                        message="Running approved GPU computation",
                        node_id=node.node_id, tool_name="sandbox_exec", profile="gpu",
                        safe_command_label=str(validated_arguments["command"][0])[:80],
                    )
                    result = await invoke(
                        "sandbox_exec", scoped_question,
                        {
                            "workspace_id": workspace_id,
                            "argv": validated_arguments["command"],
                            "workdir": "/workspace",
                            "command_timeout_seconds": min(self.timeout_seconds, 420),
                        },
                        skill_id="sandbox_workspace",
                    )
                    if getattr(result, "error", None):
                        await self._progress(
                            phase="researching", status="sandbox_failed",
                            message="Required GPU execution failed",
                            node_id=node.node_id, tool_name="sandbox_exec", profile="gpu",
                        )
                        raise ResearchInfrastructureError(str(result.error))
                    await self._progress(
                        phase="researching", status="sandbox_command_completed",
                        message="GPU execution evidence collected",
                        node_id=node.node_id, tool_name="sandbox_exec", profile="gpu",
                        **_command_result_details(result.content),
                    )
                    collected.append({
                        "query": scoped_question,
                        "content": str(result.content),
                        "title": "Validated isolated GPU execution",
                        "url": "",
                        "source_type": "sandbox_execution",
                        "credibility": 1.0,
                        "metadata": _command_result_details(result.content),
                        "entity_match": {
                            "decision": "aligned",
                            "reason": "Execution used the server-validated input frozen in the approved brief.",
                        },
                    })
                    continue
                if kind != "repository":
                    if requirement.get("required", True):
                        raise ResearchInfrastructureError(
                            f"Required {kind or 'Sandbox'} execution has no validated runnable resource"
                        )
                    continue
                repository_url = str(requirement.get("resource_reference") or "")
                if not repository_url.startswith("https://github.com/"):
                    if requirement.get("required", True):
                        raise ResearchInfrastructureError(
                            "Required repository execution has no validated public GitHub URL"
                        )
                    continue
                actions = set(requirement.get("actions") or [])
                operations = ["files", "git_summary"]
                if "run_checks" in actions:
                    operations.append("tests")
                if repository_url not in self._sandbox_announced:
                    self._sandbox_announced.add(repository_url)
                    await self._progress(
                        phase="researching", status="sandbox_created",
                        message="Creating task-scoped Modal Sandbox",
                        node_id=node.node_id, tool_name="repository_inspection",
                        profile=requirement.get("profile", "repository"),
                    )
                    await self._progress(
                        phase="researching", status="sandbox_ready",
                        message="Repository Sandbox ready",
                        node_id=node.node_id, tool_name="repository_inspection",
                        profile=requirement.get("profile", "repository"),
                    )
                await self._progress(
                    phase="researching",
                    status="sandbox_command_started",
                    message="Inspecting the approved repository in Modal Sandbox",
                    node_id=node.node_id,
                    tool_name="repository_inspection",
                    profile=requirement.get("profile", "repository"),
                    safe_command_label="repository inspection",
                )
                result = await invoke(
                    "repository_inspection",
                    scoped_question,
                    {"repository_url": repository_url, "operations": operations},
                    skill_id="repository_inspection",
                )
                if getattr(result, "error", None):
                    await self._progress(
                        phase="researching", status="sandbox_failed",
                        message="Required repository inspection failed",
                        node_id=node.node_id, tool_name="repository_inspection",
                        profile=requirement.get("profile", "repository"),
                    )
                    raise ResearchInfrastructureError(str(result.error))
                operation_results = []
                result_sources = list(getattr(result, "sources", []) or [])
                if result_sources:
                    metadata = result_sources[0].get("metadata") or {}
                    operation_results = list(metadata.get("operation_results") or [])
                await self._progress(
                    phase="researching",
                    status="sandbox_command_completed",
                    message="Repository evidence collected",
                    node_id=node.node_id,
                    tool_name="repository_inspection",
                    profile=requirement.get("profile", "repository"),
                    exit_code=max(
                        (int(item.get("exit_code", 0)) for item in operation_results),
                        default=0,
                    ),
                    elapsed_seconds=sum(
                        float(item.get("elapsed_seconds", 0.0)) for item in operation_results
                    ),
                    truncated=any(bool(item.get("truncated")) for item in operation_results),
                )
                collected.extend(await admit(_evidence_from_result(result, scoped_question)))
            return collected

        evidence.extend(await route_sandbox_tools())
        evidence.extend(await route_domain_tools())

        search = await search_with_adaptation() if calls < max_tool_calls else None
        sources = list(getattr(search, "sources", []) or []) if search is not None else []
        if search is not None:
            evidence.extend(await admit(_evidence_from_result(search, scoped_question)))

        # Fetch the most promising URLs from every discovery source (domain +
        # web), deduplicated, up to the fetch budget.
        candidate_urls = [
            str(item.get("url", ""))
            for item in evidence
            if str(item.get("url", "")).startswith(("https://", "http://"))
        ]
        # Never request more fetches than the fetch budget or the remaining
        # call budget allows; invoke() raises once the call cap is reached.
        fetch_budget = max(0, min(self.max_fetches, max_tool_calls - calls))
        urls = list(dict.fromkeys(candidate_urls))[:fetch_budget]
        if urls:
            fetched = await asyncio.gather(
                *(invoke("web_fetch", scoped_question, {"url": url, "max_characters": 50_000}) for url in urls),
                return_exceptions=True,
            )
            for item in fetched:
                # A single destination can be slow, blocked, or temporarily
                # unschedulable even while the deployed tool backend and every
                # other source are healthy. Search has already succeeded, so
                # retain the other retrieved evidence instead of failing the
                # whole report for one URL.
                if isinstance(item, ResearchInfrastructureError):
                    await self._progress(
                        phase="researching",
                        status="source_unavailable",
                        message="Skipped an unavailable source",
                        node_id=node.node_id,
                        tool_name="web_fetch",
                    )
                    continue
                if not isinstance(item, Exception):
                    evidence.extend(await admit(_evidence_from_result(item, scoped_question)))

        # A research answer is only useful to the writer when it has a
        # citable, extracted source.  Do not turn an empty search result into
        # a plausible-but-unsupported synthetic answer. Redact credential-like
        # tokens from tool output before it reaches an LLM prompt. Rank the
        # surviving records (full-text fetches ahead of snippets, deduplicated
        # by URL) because the answerer truncates to its evidence budget and
        # must not lose the fetched pages to a flood of earlier snippets.
        evidence = rank_evidence([
            _redact(item)
            for item in evidence
            if str(item.get("content", "")).strip()
            and (
                str(item.get("url", "")).startswith(("https://", "http://"))
                or item.get("source_type") == "sandbox_execution"
            )
        ])
        if not evidence:
            result = {
                "answered": False,
                "tool_calls_used": calls,
                "unresolved_gaps": ["no citable source content was retrieved"],
                "evidence": [],
            }
            await self._progress(phase="researching", status="node_completed", message=f"No citable evidence for: {node.question}", node_id=node.node_id, source_count=0)
            return result

        answer = await self.answerer(node, evidence)
        answer["tool_calls_used"] = calls
        answer["evidence"] = evidence
        answer.setdefault("answered", bool(evidence))
        await self._progress(phase="researching", status="node_completed", message=f"Evidence synthesized: {node.question}", node_id=node.node_id, source_count=len(evidence))
        return answer


def _evidence_from_result(result: Any, query: str) -> list[dict[str, Any]]:
    content = str(getattr(result, "content", "") or "")
    sources = list(getattr(result, "sources", []) or [])
    if not content and not sources:
        return []
    records = []
    for source in sources:
        source_type = source.get("source_type", "web")
        # Search results receive only their own snippet. Fetched pages have one
        # source, so their full extracted text is retained once rather than
        # copied into every search-result record.
        record_content = content if len(sources) == 1 and source_type != "web_search" else str(source.get("snippet", ""))
        records.append({
            "query": query,
            "content": record_content,
            "title": source.get("title", ""),
            "url": source.get("url", ""),
            "date": source.get("date"),
            "source_type": source_type,
            "credibility": source.get("credibility_base", 0.5),
            "metadata": source.get("metadata", {}),
        })
    return records or [{"query": query, "content": content, "title": "", "url": "", "source_type": "web", "credibility": 0.5}]


def _command_result_details(content: Any) -> dict[str, Any]:
    try:
        payload = json.loads(str(content))
    except (TypeError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    details: dict[str, Any] = {}
    if isinstance(payload.get("exit_code"), int):
        details["exit_code"] = payload["exit_code"]
    if isinstance(payload.get("elapsed_seconds"), (int, float)):
        details["elapsed_seconds"] = float(payload["elapsed_seconds"])
    if isinstance(payload.get("truncated"), bool):
        details["truncated"] = payload["truncated"]
    return details
