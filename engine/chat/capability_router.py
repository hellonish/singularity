"""Deterministic capability selection shared by chat and research."""
from __future__ import annotations

import re
import os
from dataclasses import dataclass
from typing import Literal


CapabilityKind = Literal["none", "trusted_function", "sandbox", "api_only"]

_GITHUB_URL = re.compile(
    r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?(?:/[^\s]*)?",
    re.IGNORECASE,
)
_REPOSITORY_TERMS = re.compile(
    r"\b(inspect|review|research|analy[sz]e|clone|edit|modify|test|build|lint|debug)\b"
    r".{0,64}\b(repository|repo|source\s+code|codebase|git\s+history|project\s+files?)\b|"
    r"\b(repository|repo|source\s+code|codebase)\b.{0,64}"
    r"\b(inspect|review|research|analy[sz]e|clone|edit|modify|test|build|lint|debug)\b",
    re.IGNORECASE,
)
_CODE_TERMS = re.compile(
    r"\b(execute|run|debug|compile|build|test|lint|format)\b.{0,48}\b(code|script|program|project)\b|"
    r"\b(code|script|program)\b.{0,48}\b(execute|run|debug|compile|test)\b",
    re.IGNORECASE,
)
_DATA_TERMS = re.compile(
    r"\b(analy[sz]e|compute|calculate|profile|transform|clean|plot|execute|run)\b"
    r".{0,48}\b(dataset|csv|dataframe|data|pandas|numpy)\b|\bstatistical analysis\b",
    re.IGNORECASE,
)
_GPU_TERMS = re.compile(
    r"\b(train|run|execute|benchmark|profile)\b.{0,48}"
    r"\b(gpu|cuda|pytorch|tensorflow|machine learning workload)\b",
    re.IGNORECASE,
)
_SERVICE_TERMS = re.compile(
    r"\b(start|run|test)\b.{0,40}\b(service|server|web app|api server)\b",
    re.IGNORECASE,
)
_API_ONLY_TERMS = re.compile(
    r"\b(attached report|my report|authorized resource|private document|tenant data)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CapabilityDecision:
    kind: CapabilityKind
    skill_ids: tuple[str, ...] = ()
    required: bool = False
    reason: str = "no execution capability required"
    repository_url: str | None = None


def repository_url(text: str) -> str | None:
    match = _GITHUB_URL.search(text)
    if match is None:
        return None
    value = match.group(0).rstrip(".,);]}")
    parts = value.split("/")
    return "/".join(parts[:5]).removesuffix(".git")


def select_capability(text: str) -> CapabilityDecision:
    """Choose the strongest execution boundary justified by the request."""
    repo = repository_url(text)
    if repo or _REPOSITORY_TERMS.search(text):
        return CapabilityDecision(
            kind="sandbox",
            skill_ids=("repository_inspection", "sandbox_workspace"),
            required=True,
            reason="repository evidence requires isolated filesystem inspection",
            repository_url=repo,
        )
    if _GPU_TERMS.search(text):
        return CapabilityDecision(
            kind="sandbox",
            skill_ids=("code_execution", "sandbox_workspace"),
            required=True,
            reason="GPU computation requires an explicitly selected isolated profile",
        )
    if _SERVICE_TERMS.search(text):
        return CapabilityDecision(
            kind="sandbox",
            skill_ids=("code_execution", "sandbox_workspace"),
            required=True,
            reason="service execution requires an isolated workspace and readiness checks",
        )
    if _DATA_TERMS.search(text):
        return CapabilityDecision(
            kind="sandbox",
            skill_ids=("dataset_analysis", "sandbox_workspace"),
            required=True,
            reason="dataset computation requires isolated execution",
        )
    if _CODE_TERMS.search(text):
        return CapabilityDecision(
            kind="sandbox",
            skill_ids=("code_execution", "sandbox_workspace"),
            required=True,
            reason="generated or user-requested code must execute in a Sandbox",
        )
    if _API_ONLY_TERMS.search(text):
        return CapabilityDecision(
            kind="api_only",
            skill_ids=("production_retrieval",),
            required=True,
            reason="tenant-scoped retrieval must remain behind the authenticated API",
        )
    return CapabilityDecision(kind="none")


def trusted_function_enabled(master_enabled: bool) -> bool:
    return master_enabled and _enabled("SINGULARITY_MODAL_TRUSTED_FUNCTION_ENABLED", default=True)


def sandbox_enabled(master_enabled: bool) -> bool:
    return master_enabled and _enabled("SINGULARITY_MODAL_SANDBOX_ENABLED", default=True)


def _enabled(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
