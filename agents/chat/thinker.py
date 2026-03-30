"""
Thinker — the reasoning layer that sits between user input and execution.

Given a user message + conversation history, the Thinker:
  1. Decides the mode: "chat" (1-5 steps) or "research" (5-10 steps)
  2. Selects relevant skills from the registry (0-3 for chat, any for research)
  3. Produces an ordered step plan

The plan is shown to the user BEFORE any execution begins, making the
agent fully transparent.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ThinkStep(BaseModel):
    step_id: int
    type: str            # "direct_answer" | "web_search" | "skill_call" | "analyze" | "summarize"
    description: str
    skill_name: str | None = None   # must be a key in SKILL_REGISTRY, or None


class ThinkPlan(BaseModel):
    mode: str                        # "chat" | "research"
    reasoning: str                   # Brief explanation of why this mode/plan
    selected_skills: list[str]       # Subset of skills the agent will touch
    steps: list[ThinkStep]
    strength: int = 5                # 1-10; only meaningful for research mode
    audience: str = "practitioner"   # layperson / student / practitioner / expert / executive


# ---------------------------------------------------------------------------
# Skill menu (compact, for thinker prompt)
# ---------------------------------------------------------------------------

_SKILL_MENU: dict[str, str] = {
    # Tier 1 — Retrieval
    "web_search":         "General web search via DuckDuckGo + scraping",
    "academic_search":    "Scholarly papers via Semantic Scholar / arXiv",
    "clinical_search":    "Clinical trials, PubMed medical literature",
    "legal_search":       "Case law, statutes, regulations",
    "financial_search":   "Market data, earnings, SEC filings",
    "patent_search":      "USPTO / EPO patent filings",
    "news_archive":       "News archives and recent press",
    "standards_search":   "ISO / IEEE / NIST standards",
    "forum_search":       "Reddit, HN, Stack Overflow discussions",
    "video_search":       "YouTube transcripts and video content",
    "dataset_search":     "Kaggle, HuggingFace, data repositories",
    "gov_search":         "Government data and official publications",
    "book_search":        "Books, Google Books, Open Library",
    "social_search":      "Twitter / X, LinkedIn public posts",
    "pdf_deep_extract":   "Deep PDF parsing, tables, figures",
    "multimedia_search":  "Images, diagrams, infographics",
    "code_search":        "GitHub code, documentation, APIs",
    "data_extraction":    "Structured data extraction from pages",
    # Tier 2 — Analysis
    "synthesis":            "Combine multi-source findings into coherent summary",
    "comparative_analysis": "Side-by-side comparison of options/entities",
    "gap_analysis":         "Identify what's missing in available evidence",
    "quality_check":        "Evaluate source quality and evidence strength",
    "contradiction_detect": "Find conflicting claims across sources",
    "claim_verification":   "Fact-check specific claims against evidence",
    "causal_analysis":      "Identify cause-effect relationships",
    "statistical_analysis": "Interpret data, statistics, significance",
    "meta_analysis":        "Aggregate findings across multiple studies",
    "trend_analysis":       "Identify patterns and trends over time",
    "timeline_construct":   "Build chronological event timeline",
    "hypothesis_gen":       "Generate testable hypotheses from evidence",
    "entity_extraction":    "Extract named entities, dates, locations",
    "citation_graph":       "Map citation relationships between papers",
    "sentiment_cluster":    "Cluster by sentiment / opinion",
    "credibility_score":    "Score source credibility and bias",
    "translation":          "Translate non-English content",
    "fallback_router":      "Route to best available skill when primary fails",
    # Tier 3 — Output
    "report_generator":   "Full structured research report",
    "exec_summary":       "Executive summary (concise overview)",
    "bibliography_gen":   "Formatted bibliography / references",
    "decision_matrix":    "Structured decision framework",
    "explainer":          "Plain-language explanation for laypersons",
    "annotation_gen":     "Annotate sources with commentary",
    "visualization_spec": "Specify charts / data visualizations",
    "knowledge_delta":    "Highlight what's new vs. prior knowledge",
}


def _skill_menu_text() -> str:
    """Compact skill list for the thinker prompt."""
    lines = []
    for name, desc in _SKILL_MENU.items():
        lines.append(f"  {name:<24} — {desc}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_THINKER_SYSTEM = """\
You are the THINKING LAYER of a dual-mode AI agent. Your job is to:

1. Read the user's message and conversation history
2. Decide the RIGHT mode:
   - "chat": for factual questions, explanations, coding help, quick lookups (1-5 steps)
   - "research": for deep analysis, multi-source investigations, long-form research (5-10 steps)
3. Select the most relevant skills from the registry (0-3 for chat, any for research)
4. Produce a clear, ordered step plan

SKILL REGISTRY (44 skills across 3 tiers):
{skill_menu}

STEP TYPES:
  direct_answer  — Answer from LLM knowledge alone (no tool needed)
  web_search     — Live web search
  skill_call     — Invoke a specific skill from the registry
  analyze        — Reason over accumulated context
  summarize      — Condense findings into a final answer

RULES:
- Chat mode: 1-5 steps max. Be minimal. Most simple questions need only "direct_answer".
- Research mode: 5-10 steps. Must include retrieval + analysis + synthesis.
- Extended thinking: if user requested extended, you MAY use research mode even for simpler questions.
- selected_skills: list the skill names you'll use. Empty list [] if no skills needed.
- strength: 1-4 for chat, 5-7 for moderate research, 8-10 for deep research.
- audience: infer from message tone (layperson / student / practitioner / expert / executive).
- reasoning: 1-2 sentences explaining your choice.

Output ONLY valid JSON matching this exact schema — no prose, no markdown fences.
""".format(skill_menu=_skill_menu_text())


# ---------------------------------------------------------------------------
# Thinker
# ---------------------------------------------------------------------------

class Thinker:
    """
    Calls an LLM to produce a ThinkPlan for a given user message.
    """

    def __init__(self, client) -> None:
        self._client = client

    def think(
        self,
        message: str,
        history: list[dict[str, str]],
        extended: bool = False,
    ) -> ThinkPlan:
        """
        Synchronous call — returns a ThinkPlan.

        Args:
            message:   The latest user message.
            history:   List of {"role": "user"|"assistant", "content": "..."}.
                       Last 5 turns max (caller's responsibility to trim).
            extended:  Whether extended thinking mode is active (allows research).
        """
        history_block = ""
        if history:
            lines = []
            for turn in history[-5:]:
                role = turn["role"].upper()
                content = turn["content"][:300]  # truncate long turns
                lines.append(f"[{role}]: {content}")
            history_block = "\nConversation history (last 5 turns):\n" + "\n".join(lines) + "\n"

        extended_note = (
            "\nNOTE: Extended thinking is ACTIVE. You may use research mode for complex questions "
            "and increase step count up to 10.\n"
            if extended else ""
        )

        prompt = (
            f"{history_block}"
            f"{extended_note}"
            f"\nUser message: {message}\n\n"
            "Produce a ThinkPlan JSON object."
        )

        return self._client.generate_structured(
            prompt=prompt,
            system_prompt=_THINKER_SYSTEM,
            schema=ThinkPlan,
            temperature=0.3,
            max_tokens=1500,
        )
