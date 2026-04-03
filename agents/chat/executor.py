"""
Chat-mode step executor.

Runs a ThinkPlan in Chat Mode (1-5 steps) by executing each step
sequentially and accumulating context. Yields text chunks for streaming.

Step types handled:
  direct_answer      — LLM streaming from knowledge (auto-falls back to web if uncertain)
  web_search         — Lightweight DuckDuckGo + scrape (no Qdrant)
  skill_call         — Invoke skill from SKILL_REGISTRY via a summarise-only path
  analyze            — LLM reasoning over accumulated context
  claim_verification — Fact-check style pass over gathered context
  summarize          — Final condensing LLM call
  synthesis          — Same execution path as summarize (final woven answer)
  (other types)      — Generic reasoning step with a human-readable label
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from agents.chat.thinker import ThinkPlan, ThinkStep

_HUMAN_STEP_LABELS: dict[str, str] = {
    "direct_answer": "Answer",
    "web_search": "Web search",
    "skill_call": "Skill",
    "analyze": "Analysis",
    "summarize": "Summary",
    "synthesis": "Synthesis",
    "claim_verification": "Claim verification",
}


def _human_step_label(step_type: str) -> str:
    """Title for user-visible step lines; avoids raw snake_case in chat."""
    if step_type in _HUMAN_STEP_LABELS:
        return _HUMAN_STEP_LABELS[step_type]
    return step_type.replace("_", " ").strip().title()

_CHAT_DIR = Path(__file__).parent
SINGULARITY_IDENTITY = (_CHAT_DIR / "identity.md").read_text(encoding="utf-8")
_RESPONSE_SYSTEM     = (_CHAT_DIR / "response_system_prompt.md").read_text(encoding="utf-8")
_SUMMARIZE_SYSTEM    = (_CHAT_DIR / "summarize_system_prompt.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Uncertainty detection — triggers auto web-search fallback
# ---------------------------------------------------------------------------

_UNCERTAINTY_PHRASES = [
    r"based on my (knowledge|training|last update)",
    r"as of my (knowledge|last update|cutoff)",
    r"i (don'?t|do not) (have|find) (information|details|data)",
    r"i('?m| am) not (aware|familiar|sure)",
    r"i (can'?t|cannot) (find|confirm|verify)",
    r"doesn'?t appear to (be|exist)",
    r"there doesn'?t appear",
    r"no (product|app|feature|service).*named",
    r"i (have no|lack) (information|data|details)",
    r"my knowledge.*\b(limited|cut.?off)\b",
    r"(might|may) (be|have) (changed|updated) since",
]
_UNCERTAINTY_RE = re.compile("|".join(_UNCERTAINTY_PHRASES), re.IGNORECASE)


def _is_uncertain(text: str) -> bool:
    """Returns True if the response signals the model lacks knowledge."""
    return bool(_UNCERTAINTY_RE.search(text))



_IDENTITY_RE = re.compile(
    r"\b(who|what)\s+(are|is)\s+you\b"
    r"|\byour\s+(name|identity)\b"
    r"|\bintroduce\s+yourself\b"
    r"|\bwhat\s+can\s+you\s+do\b",
    re.IGNORECASE,
)


def _is_identity_query(message: str) -> bool:
    return bool(_IDENTITY_RE.search(message))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _web_search_lightweight(query: str, n: int = 5) -> str:
    """
    Lightweight web search using WebFetchTool directly — no Qdrant, no vector store.
    Returns a plain-text content block suitable for LLM context.
    """
    try:
        from tools.web_fetch import WebFetchTool
        tool = WebFetchTool()
        result = await tool.call_with_retry(query, max_results=n)

        if not result or not result.ok:
            return f"[No results found for: {query}]"

        lines = []
        for i, src in enumerate(result.sources[:n], 1):
            title   = src.get("title", "")
            snippet = src.get("snippet", "")[:400]
            url     = src.get("url", "")
            lines.append(f"{i}. **{title}**\n   {snippet}\n   Source: {url}")
        return "\n\n".join(lines) if lines else result.content

    except Exception as exc:
        logger.warning("[web_search] lightweight call failed: %s", exc)
        return f"[Web search failed: {exc}]"


def _skill_summary(skill_name: str, query: str, client) -> str:
    """
    Invoke a skill's summarise-mode: ask the LLM what this skill contributes.
    Used as a lightweight stand-in for full skill execution in chat mode.
    """
    try:
        from skills import SKILL_REGISTRY
        skill = SKILL_REGISTRY.get(skill_name)
        if skill is None:
            return f"[Skill '{skill_name}' not found in registry]"

        skill_desc = getattr(skill, "description", skill_name)
        prompt = (
            f"You are acting as the '{skill_name}' skill ({skill_desc}).\n"
            f"Given the research question: \"{query}\"\n"
            f"Provide the most relevant information or analysis you can "
            f"from your domain knowledge. Be specific and factual. "
            f"Return 150-300 words."
        )
        return client.generate_text(
            prompt=prompt,
            system_prompt=f"You are the {skill_name} specialist. Be precise and factual.",
            temperature=0.4,
        )
    except Exception as exc:
        logger.warning("[skill_call] %s failed: %s", skill_name, exc)
        return f"[Skill {skill_name} encountered an error: {exc}]"


# ---------------------------------------------------------------------------
# Step executor
# ---------------------------------------------------------------------------

class ChatModeExecutor:
    """
    Executes a chat-mode ThinkPlan step by step.

    Each step accumulates into `context_chunks`, which are fed into
    subsequent LLM calls so the agent can reason across steps.

    Key behaviours:
    - direct_answer: if response shows uncertainty → auto web-search fallback
    - identity queries: returns Singularity intro immediately
    - no audience calibration phrases ever appear in output
    """

    def __init__(self, client) -> None:
        self._client = client

    async def execute(
        self,
        plan: ThinkPlan,
        user_message: str,
        history: list[dict[str, str]],
    ) -> AsyncGenerator[str, None]:
        """
        Yields text chunks as the plan executes.

        Yields a special marker line:
          "§STEP:{step_id}:{type}:{description}\n"
        before each step so the CLI can render step headers.
        """
        # ── Identity shortcut ──────────────────────────────────────────
        if _is_identity_query(user_message):
            yield "§STEP:1:identity:Introducing Singularity\n"
            yield SINGULARITY_IDENTITY
            return

        context_chunks: list[str] = []

        history_block = ""
        if history:
            parts = []
            for turn in history[-5:]:
                parts.append(f"{turn['role'].upper()}: {turn['content'][:200]}")
            history_block = "\n".join(parts) + "\n\n"

        for step in plan.steps:
            yield f"§STEP:{step.step_id}:{step.type}:{step.description}\n"

            # ── direct_answer ──────────────────────────────────────────
            if step.type == "direct_answer":
                context_joined = "\n\n".join(context_chunks) if context_chunks else ""
                ctx_block = f"\nContext gathered:\n{context_joined}\n\n" if context_joined else ""
                prompt = (
                    f"{history_block}"
                    f"User question: {user_message}\n\n"
                    f"{ctx_block}"
                    "Provide a comprehensive, accurate answer. "
                    "If context is available above, integrate it naturally."
                )

                # Collect full response to check for uncertainty
                full_text_parts: list[str] = []
                for chunk in self._client.generate_text_stream(
                    prompt=prompt,
                    system_prompt=_RESPONSE_SYSTEM,
                    temperature=0.5,
                ):
                    full_text_parts.append(chunk)

                full_text = "".join(full_text_parts)

                # Auto web-search fallback if model signals uncertainty
                if _is_uncertain(full_text):
                    yield "\n\n*⚡ Knowledge gap detected — fetching live web results...*\n\n"
                    web_result = await _web_search_lightweight(user_message, n=6)
                    context_chunks.append(f"[Live Web Search]\n{web_result}")

                    # Re-answer with web context
                    re_prompt = (
                        f"{history_block}"
                        f"User question: {user_message}\n\n"
                        f"Live search results:\n{web_result}\n\n"
                        "Answer the user's question using the search results above. "
                        "Cite sources naturally in your response."
                    )
                    for chunk in self._client.generate_text_stream(
                        prompt=re_prompt,
                        system_prompt=_RESPONSE_SYSTEM,
                        temperature=0.5,
                    ):
                        yield chunk
                else:
                    yield full_text

            # ── web_search ─────────────────────────────────────────────
            elif step.type == "web_search":
                result = await _web_search_lightweight(step.description, n=5)
                context_chunks.append(f"[Web Search: {step.description}]\n{result}")
                yield "\n*🌐 Web search complete.*\n"

            # ── skill_call ─────────────────────────────────────────────
            elif step.type == "skill_call":
                skill_name = step.skill_name or "web_search"
                result = await asyncio.to_thread(
                    _skill_summary, skill_name, step.description, self._client
                )
                context_chunks.append(f"[{skill_name}: {step.description}]\n{result}")
                yield f"\n*🔧 Used `{skill_name}`.*\n"

            # ── analyze ────────────────────────────────────────────────
            elif step.type == "analyze":
                context_joined = "\n\n---\n\n".join(context_chunks)
                prompt = (
                    f"{history_block}"
                    f"User question: {user_message}\n\n"
                    f"Information gathered:\n{context_joined}\n\n"
                    f"Task: {step.description}\n\n"
                    "Provide a focused, evidence-based analysis."
                )
                analysis = await asyncio.to_thread(
                    self._client.generate_text,
                    prompt,
                    "You are an expert analyst. Prior turns may bind scope or meaning for the latest "
                    "message; integrate them when relevant. Be precise, cite evidence, avoid stating audience type.",
                    0.4,
                )
                context_chunks.append(f"[Analysis]\n{analysis}")
                yield "\n*🔍 Analysis complete.*\n"

            # ── claim_verification ─────────────────────────────────────
            elif step.type == "claim_verification":
                context_joined = "\n\n---\n\n".join(context_chunks)
                prompt = (
                    f"{history_block}"
                    f"User question: {user_message}\n\n"
                    f"Information gathered:\n{context_joined}\n\n"
                    f"Verification task: {step.description}\n\n"
                    "Assess which claims are well supported by the gathered information, "
                    "which need caveats or uncertainty language, and which lack evidence. "
                    "Be precise; do not invent sources."
                )
                verified = await asyncio.to_thread(
                    self._client.generate_text,
                    prompt,
                    "You are a careful fact-checker. Earlier user turns may define which claims to "
                    "verify; do not ignore them. Cite what the context does or does not support.",
                    0.3,
                )
                context_chunks.append(f"[Claim verification]\n{verified}")
                yield "\n*Claim verification complete.*\n"

            # ── summarize / synthesis ────────────────────────────────────
            elif step.type in ("summarize", "synthesis"):
                if step.type == "synthesis":
                    yield "\n*Synthesis*\n"
                context_joined = "\n\n---\n\n".join(context_chunks)
                prompt = (
                    f"{history_block}"
                    f"User question: {user_message}\n\n"
                    f"All gathered information:\n{context_joined}\n\n"
                    f"Task: {step.description}\n\n"
                    "Write the final response. Be direct, well-structured, and comprehensive."
                )
                for chunk in self._client.generate_text_stream(
                    prompt=prompt,
                    system_prompt=_SUMMARIZE_SYSTEM,
                    temperature=0.5,
                ):
                    yield chunk

            else:
                label = _human_step_label(step.type)
                context_joined = "\n\n---\n\n".join(context_chunks)
                prompt = (
                    f"{history_block}"
                    f"User question: {user_message}\n\n"
                    f"Information gathered:\n{context_joined}\n\n"
                    f"{label}: {step.description}\n\n"
                    "Address the task using only the gathered information; "
                    "flag gaps or uncertainty where appropriate."
                )
                fallback = await asyncio.to_thread(
                    self._client.generate_text,
                    prompt,
                    "You are a precise research assistant. Use prior turns when they constrain "
                    "or clarify the latest message. Avoid audience calibration phrases.",
                    0.4,
                )
                context_chunks.append(f"[{label}]\n{fallback}")
                yield f"\n*{label} complete.*\n"
