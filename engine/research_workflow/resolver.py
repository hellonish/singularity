from __future__ import annotations

import asyncio
import re
import time
from inspect import isawaitable
from collections.abc import Awaitable, Callable
from typing import Any

from engine.chat.effort import ChatEffort
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

    def __init__(self, executor, answerer: Answerer, *, timeout_seconds: int = 60, max_fetches: int = 2, max_search_variants: int = 3, progress_reporter=None):
        self.executor = executor
        self.answerer = answerer
        self.timeout_seconds = timeout_seconds
        self.max_fetches = max(0, min(max_fetches, RunCaps.MAX_FETCHES_CEILING))
        # How many reformulation attempts web_search may make. Production uses
        # the full set; test mode sets this to 1 so a run makes exactly one
        # real search call.
        self.max_search_variants = max(1, min(max_search_variants, 3))
        self.progress_reporter = progress_reporter

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
                "tool_call" if event.get("status") in self._TOOL_CALL_STATUSES else "phase",
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
        await self._progress(phase="researching", status="node_started", message=f"Researching: {node.question}", node_id=node.node_id)

        async def invoke(tool_name: str, query: str, arguments: dict[str, Any], *, skill_id: str = "general_web_research") -> Any:
            """Dispatch one logical tool call, retrying transparently on
            infrastructure errors. Consumes exactly one unit of the research
            budget regardless of how many Modal-level retries it takes.

            Raises ResearchInfrastructureError if the Modal backend stays
            unreachable after every attempt. A failed search is run-fatal;
            a failed individual page fetch is handled below as a source-level
            failure because the rest of the evidence may still be usable.
            """
            nonlocal calls
            if calls >= max_tool_calls:
                raise RuntimeError("research node tool-call cap exhausted")
            calls += 1
            invocation = ChatToolInvocation(
                run_id=f"research-node:{node.node_id}",
                skill_id=skill_id,
                tool_name=tool_name,
                query=query,
                arguments=arguments,
                effort=ChatEffort.MEDIUM,
                timeout_seconds=self.timeout_seconds,
            )
            await self._progress(phase="researching", status="tool_dispatched", message=f"Requesting Modal worker for {tool_name}", node_id=node.node_id, tool_name=tool_name)
            started = time.monotonic()
            last_exc: Exception | None = None
            for attempt in range(_MODAL_DISPATCH_ATTEMPTS):
                try:
                    result = await self.executor.execute(invocation)
                    error = getattr(result, "error", None)
                    sources = list(getattr(result, "sources", []) or [])
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
                    if attempt < _MODAL_DISPATCH_ATTEMPTS - 1:
                        await self._progress(phase="researching", status="tool_retry", message=f"{tool_name} unreachable — retrying ({attempt + 1}/{_MODAL_DISPATCH_ATTEMPTS - 1})", node_id=node.node_id, tool_name=tool_name, error=type(exc).__name__)
                        await asyncio.sleep(2 ** attempt)
            # Every dispatch attempt failed: the backend, not the query, is the
            # problem. Signal a run-level abort with a user-facing message.
            await self._progress(phase="researching", status="tool_failed", message=f"{tool_name} failed", node_id=node.node_id, tool_name=tool_name, elapsed_seconds=time.monotonic() - started, error=type(last_exc).__name__ if last_exc else "unknown")
            raise ResearchInfrastructureError(
                f"{tool_name} dispatch failed after {_MODAL_DISPATCH_ATTEMPTS} attempts: {last_exc}"
            ) from last_exc

        async def search_with_adaptation() -> Any:
            """Run web_search, reformulating the query when it comes back empty
            or errored, until the search succeeds or the call budget is spent.

            A Modal outage propagates as ResearchInfrastructureError from
            invoke(); an empty/errored *result* is a soft failure the agent
            adapts around with a reworded query.
            """
            variants = [
                (node.question, {"max_results": 8}),
                (f"{node.question} primary source", {"max_results": 5}),
                (f"{node.question} report OR study OR data", {"max_results": 5}),
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
                result = await invoke(tool_name, node.question, {"max_results": 8}, skill_id=skill_id)
                if getattr(result, "error", None):
                    continue
                records = _evidence_from_result(result, node.question)
                if records:
                    collected.extend(records)
            return collected

        evidence.extend(await route_domain_tools())

        search = await search_with_adaptation() if calls < max_tool_calls else None
        sources = list(getattr(search, "sources", []) or []) if search is not None else []
        if search is not None:
            evidence.extend(_evidence_from_result(search, node.question))

        # Fetch the most promising URLs from every discovery source (domain +
        # web), deduplicated, up to the fetch budget.
        candidate_urls = [
            str(item.get("url", ""))
            for item in evidence
            if str(item.get("url", "")).startswith(("https://", "http://"))
        ]
        candidate_urls += [str(source.get("url", "")) for source in sources if source.get("url")]
        # Never request more fetches than the fetch budget or the remaining
        # call budget allows; invoke() raises once the call cap is reached.
        fetch_budget = max(0, min(self.max_fetches, max_tool_calls - calls))
        urls = list(dict.fromkeys(candidate_urls))[:fetch_budget]
        if urls:
            fetched = await asyncio.gather(
                *(invoke("web_fetch", node.question, {"url": url, "max_characters": 50_000}) for url in urls),
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
                    evidence.extend(_evidence_from_result(item, node.question))

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
            and str(item.get("url", "")).startswith(("https://", "http://"))
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
