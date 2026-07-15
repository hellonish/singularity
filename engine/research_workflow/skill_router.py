"""Compact, deterministic skill shortlisting for research node resolution."""
from __future__ import annotations

from dataclasses import dataclass

from engine.skills import SKILL_REGISTRY


@dataclass(frozen=True)
class SelectedSkills:
    ids: tuple[str, ...]
    instructions: str


_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("code", "python", "script", "execute", "run tests", "debug"), "code_execution"),
    (("repository", "repo", "github", "source code"), "repository_inspection"),
    (("dataset", "csv", "dataframe", "pandas"), "dataset_analysis"),
    (("medical", "clinical", "drug", "disease", "pubmed"), "medical_research"),
    (("financial", "company filing", "sec", "revenue", "earnings"), "financial_research"),
    (("calculate", "calculation", "percentage", "arithmetic"), "quantitative_analysis"),
    (("time", "timezone", "date today"), "temporal_reasoning"),
    (("paper", "papers", "academic", "arxiv", "sources"), "source_discovery"),
)


def select_skills(query: str, *, limit: int = 3) -> SelectedSkills:
    normalized = " ".join(query.lower().split())
    selected: list[str] = []
    for phrases, skill_id in _RULES:
        if any(phrase in normalized for phrase in phrases) and skill_id not in selected:
            try:
                SKILL_REGISTRY.get(skill_id)
            except KeyError:
                continue
            selected.append(skill_id)
            if len(selected) >= limit:
                break
    if len(selected) < limit:
        selected.append("general_web_research")
    ids = tuple(dict.fromkeys(selected))[:limit]
    instructions = "\n\n".join(
        f"Skill {skill_id}:\n{SKILL_REGISTRY.get(skill_id).instructions}"
        for skill_id in ids
    )
    return SelectedSkills(ids=ids, instructions=instructions)
