"""Opt-in, live integration tests for every trusted research tool.

These tests call real public providers: they do not mock tool implementations
or HTTP clients.  Each invocation writes a compact, machine-readable result to
``tests/outputs/tools/live/<tool>.json`` so the input and observed output can
be inspected after a run without retaining large raw provider payloads.

Run deliberately, because public APIs can rate limit or change their results:

    SINGULARITY_RUN_LIVE_TOOL_TESTS=1 python -m pytest tests/tools -m integration

Include the anonymous APIs with long rate-limit backoffs only when capacity is
available:

    SINGULARITY_RUN_LIVE_TOOL_TESTS=1 SINGULARITY_RUN_RATE_SENSITIVE_TOOL_TESTS=1 \
      python -m pytest tests/tools -m integration
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from engine.tools import TOOL_REGISTRY
from engine.tools.arxiv_api import ArxivTool
from engine.tools.clinicaltrials import ClinicalTrialsTool
from engine.tools.courtlistener import CourtListenerTool
from engine.tools.dataset_hub import DatasetHubTool
from engine.tools.github_api import GitHubTool
from engine.tools.google_books import GoogleBooksTool
from engine.tools.pdf_reader import PdfReaderTool
from engine.tools.pubmed_api import PubMedTool
from engine.tools.sec_edgar import SecEdgarTool
from engine.tools.semantic_scholar import SemanticScholarTool
from engine.tools.standards_fetch import StandardsFetchTool
from engine.tools.translation import TranslationTool
from engine.tools.web_fetch import WebFetchTool
from engine.tools.web_search import WebSearchTool
from engine.tools.youtube_transcript import YouTubeTranscriptTool


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("SINGULARITY_RUN_LIVE_TOOL_TESTS") != "1",
        reason="Set SINGULARITY_RUN_LIVE_TOOL_TESTS=1 to call live tool providers.",
    ),
]

_OUTPUT_DIR = Path(__file__).parents[1] / "outputs" / "tools" / "live"
_SECRET_QUERY_VALUE = re.compile(
    r"(?i)(api[_-]?key|apikey|token|authorization)(=|%3d)([^&\s'\"]+)"
)


@dataclass(frozen=True)
class LiveToolCase:
    name: str
    tool_class: type
    query: str
    kwargs: dict[str, Any] = field(default_factory=lambda: {"max_results": 3})
    expected_source_type: str = ""
    required_env: str | None = None
    required_switch: str | None = None
    unset_env: tuple[str, ...] = ()


CASES = (
    LiveToolCase("arxiv", ArxivTool, "transformer attention architecture", expected_source_type="academic"),
    LiveToolCase("clinicaltrials", ClinicalTrialsTool, "GLP-1 obesity phase 3", expected_source_type="clinical"),
    LiveToolCase("courtlistener", CourtListenerTool, "Carpenter v United States cell phone location", expected_source_type="legal"),
    LiveToolCase("dataset_hub", DatasetHubTool, "squad", expected_source_type="dataset"),
    # GitHub public search is a supported no-token path.  Keep this baseline
    # contract independent of a developer's expired or over-scoped token.
    LiveToolCase(
        "github", GitHubTool, "fastapi", expected_source_type="code",
        unset_env=("GITHUB_TOKEN",),
    ),
    LiveToolCase("google_books", GoogleBooksTool, "Designing Data-Intensive Applications", expected_source_type="book"),
    LiveToolCase(
        "pdf_reader",
        PdfReaderTool,
        "Attention Is All You Need",
        kwargs={"url": "https://arxiv.org/pdf/1706.03762"},
        expected_source_type="pdf",
    ),
    LiveToolCase(
        "pubmed",
        PubMedTool,
        "mRNA vaccine randomized controlled trial",
        expected_source_type="academic",
        required_env="NCBI_EMAIL",
    ),
    LiveToolCase("sec_edgar", SecEdgarTool, "artificial intelligence risk disclosure", expected_source_type="financial"),
    LiveToolCase(
        "semantic_scholar", SemanticScholarTool, "attention is all you need",
        expected_source_type="academic",
        # The anonymous API may wait through a multi-minute 429 backoff.
        required_switch="SINGULARITY_RUN_RATE_SENSITIVE_TOOL_TESTS",
    ),
    # NIST search is public.  IEEE is optional, so an invalid local key must
    # not leak into an artifact or make the baseline provider test nonportable.
    LiveToolCase(
        "standards_fetch", StandardsFetchTool, "zero trust architecture",
        expected_source_type="standard", unset_env=("IEEE_API_KEY",),
    ),
    LiveToolCase(
        "translation",
        TranslationTool,
        "Bonjour, comment allez-vous?",
        kwargs={"source_lang": "fr", "target_lang": "en"},
        expected_source_type="translation",
    ),
    LiveToolCase("web_search", WebSearchTool, "NIST zero trust architecture", expected_source_type="web_search"),
    LiveToolCase(
        "web_fetch",
        WebFetchTool,
        "Read example page",
        kwargs={"url": "https://example.com", "max_characters": 10_000},
        expected_source_type="web_page",
    ),
    LiveToolCase(
        "youtube_transcript", YouTubeTranscriptTool, "MIT transformer attention lecture",
        expected_source_type="video",
        # Transcript availability and YouTube anti-bot limits vary by network.
        required_switch="SINGULARITY_RUN_RATE_SENSITIVE_TOOL_TESTS",
    ),
)


def _write_observation(case: LiveToolCase, result: Any) -> Path:
    """Persist only stable, inspectable fields; raw provider payloads stay out."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    observation = {
        "tool": case.name,
        "input": {"query": case.query, **case.kwargs},
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "ok": result.ok,
        "error": _redact(result.error),
        "credibility_base": result.credibility_base,
        "source_count": len(result.sources),
        "sources": [
            {
                "title": source.get("title"),
                "url": source.get("url"),
                "snippet": source.get("snippet"),
                "date": source.get("date"),
                "source_type": source.get("source_type"),
                "credibility_base": source.get("credibility_base"),
                "metadata": source.get("metadata", {}),
            }
            for source in result.sources
        ],
    }
    output = _OUTPUT_DIR / f"{case.name}.json"
    output.write_text(json.dumps(observation, indent=2, ensure_ascii=False, default=str) + "\n")
    return output


def _redact(value: str | None) -> str:
    return _SECRET_QUERY_VALUE.sub(r"\1\2[REDACTED]", value or "")


def test_live_cases_cover_the_registered_tool_surface():
    """A new trusted tool cannot silently miss the live integration manifest."""
    deterministic_or_deployed_only = {"calculator", "current_time", "browser_render"}
    expected = {
        descriptor.name
        for descriptor in TOOL_REGISTRY.descriptors()
        if descriptor.execution_kind == "trusted_function" and descriptor.name not in deterministic_or_deployed_only
    }
    assert {case.name for case in CASES} == expected


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
async def test_tool_with_real_input_writes_real_output(case: LiveToolCase, monkeypatch):
    if case.required_env and not os.getenv(case.required_env):
        pytest.skip(f"{case.required_env} is required by {case.name}")
    if case.required_switch and os.getenv(case.required_switch) != "1":
        pytest.skip(f"Set {case.required_switch}=1 to run the rate-sensitive {case.name} provider test")
    for env_name in case.unset_env:
        monkeypatch.delenv(env_name, raising=False)

    result = await case.tool_class().call_with_retry(case.query, timeout=90, **case.kwargs)
    output = _write_observation(case, result)

    assert result.ok, f"{case.name} failed; inspect {output}: {_redact(result.error)}"
    assert result.sources, f"{case.name} returned no sources; inspect {output}"
    assert all(
        source.get("source_type") == case.expected_source_type
        for source in result.sources
    ), f"{case.name} returned an unexpected source type; inspect {output}"
