from __future__ import annotations

import asyncio
import time
from inspect import isawaitable
from collections.abc import Awaitable, Callable
from typing import Any

from engine.chat.effort import ChatEffort
from engine.tools.contracts import ChatToolInvocation

from .dag import ResearchNode
from .runtime import ResearchInfrastructureError


Answerer = Callable[[ResearchNode, list[dict[str, Any]]], Awaitable[dict[str, Any]]]

# How many times a single Modal dispatch is retried on an infrastructure-level
# error (channel drop, timeout, remote raise) before we treat the backend as
# down. These retries are transparent to the four-call research budget: they
# re-attempt the *same* logical call rather than spending a new one.
_MODAL_DISPATCH_ATTEMPTS = 3


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
        self.max_fetches = max(0, min(max_fetches, 2))
        # How many reformulation attempts web_search may make. Production uses
        # the full set; test mode sets this to 1 so a run makes exactly one
        # real search call.
        self.max_search_variants = max(1, min(max_search_variants, 3))
        self.progress_reporter = progress_reporter

    async def _progress(self, **event: Any) -> None:
        if self.progress_reporter is not None:
            result = self.progress_reporter(event)
            if isawaitable(result):
                await result

    async def __call__(self, node: ResearchNode, max_tool_calls: int = 4) -> dict[str, Any]:
        if max_tool_calls != 4:
            raise ValueError("research node resolver requires a four-call budget")
        calls = 0
        evidence: list[dict[str, Any]] = []
        await self._progress(phase="researching", status="node_started", message=f"Researching: {node.question}", node_id=node.node_id)

        async def invoke(tool_name: str, query: str, arguments: dict[str, Any]) -> Any:
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
                skill_id="general_web_research",
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

        search = await search_with_adaptation()
        sources = list(getattr(search, "sources", []) or []) if search is not None else []
        if search is not None:
            evidence.extend(_evidence_from_result(search, node.question))

        urls = [str(source.get("url", "")) for source in sources if source.get("url")]
        urls = list(dict.fromkeys(urls))[:self.max_fetches]
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
        # a plausible-but-unsupported synthetic answer.
        evidence = [
            item for item in evidence
            if str(item.get("content", "")).strip()
            and str(item.get("url", "")).startswith(("https://", "http://"))
        ]
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
