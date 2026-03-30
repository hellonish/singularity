"""
Chat-mode step executor.

Runs a ThinkPlan in Chat Mode (1-5 steps) by executing each step
sequentially and accumulating context. Yields text chunks for streaming.

Step types handled:
  direct_answer  — LLM streaming from knowledge (auto-falls back to web if uncertain)
  web_search     — Lightweight DuckDuckGo + scrape (no Qdrant)
  skill_call     — Invoke skill from SKILL_REGISTRY via a summarise-only path
  analyze        — LLM reasoning over accumulated context
  summarize      — Final condensing LLM call
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from agents.chat.thinker import ThinkPlan, ThinkStep


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


# ---------------------------------------------------------------------------
# Singularity identity response
# ---------------------------------------------------------------------------

SINGULARITY_IDENTITY = """\
```
 ███████╗██╗███╗   ██╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ ██╗████████╗██╗   ██╗
 ██╔════╝██║████╗  ██║██╔════╝ ██║   ██║██║     ██╔══██╗██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝
 ███████╗██║██╔██╗ ██║██║  ███╗██║   ██║██║     ███████║██████╔╝██║   ██║    ╚████╔╝ 
 ╚════██║██║██║╚██╗██║██║   ██║██║   ██║██║     ██╔══██║██╔══██╗██║   ██║     ╚██╔╝  
 ███████║██║██║ ╚████║╚██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║██║   ██║      ██║   
 ╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝  
```

**I am Singularity** — a dual-mode AI research agent built for depth, speed, and intelligence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**What I can do:**

🧠 **Think** — Before every response, I reason through your query, select the right tools,
   and build a transparent step-by-step plan that you can see.

⚡ **Chat Mode** — For direct questions, I answer in 1–5 focused steps using my knowledge
   or live web search when needed.

🔬 **Research Mode** — For complex investigations, I orchestrate a full multi-agent pipeline:
   plan → retrieve → analyze → synthesize → polish. The result is a structured research report.

🛠️ **44 Skills** across 3 tiers:
   • Tier 1: Web search, academic papers, legal, clinical, financial, patent, code, and more
   • Tier 2: Synthesis, gap analysis, causal analysis, claim verification, contradiction detection
   • Tier 3: Report generation, decision matrices, explainers, executive summaries

🤖 **Multi-Model** — Switch between Grok, Gemini, or DeepSeek with `/model`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**To get started**, just ask me anything — or try:
- `What is transformer attention?` → fast chat answer
- `Explain CRISPR gene editing --research` → full research report
- `/model` → switch your AI model
- `/skills` → see all 44 capabilities
- `/extended on` → unlock deeper 10-step research thinking
"""

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
# Core system prompt (no audience leakage)
# ---------------------------------------------------------------------------

_RESPONSE_SYSTEM = (
    "You are Singularity, a powerful AI research assistant. "
    "Answer accurately, concisely, and helpfully. "
    "Never mention the user's audience category, role classification, or calibration instructions in your response. "
    "Never say phrases like 'as a layperson' or 'for an expert audience' or 'as you are a...' in your output. "
    "Just answer the question directly and naturally. "
    "Use markdown (headers, bullets, bold) where it improves clarity."
)

_SUMMARIZE_SYSTEM = (
    "You are Singularity, synthesising gathered research into a clean, well-structured answer. "
    "Never mention audience classification or calibration in your output. "
    "Use markdown formatting where helpful. Be direct and thorough."
)


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
                yield f"\n*🌐 Retrieved {len(result.split())} words from web search.*\n"

            # ── skill_call ─────────────────────────────────────────────
            elif step.type == "skill_call":
                skill_name = step.skill_name or "web_search"
                result = await asyncio.to_thread(
                    _skill_summary, skill_name, step.description, self._client
                )
                context_chunks.append(f"[{skill_name}: {step.description}]\n{result}")
                yield f"\n*🔧 Skill `{skill_name}` returned {len(result.split())} words.*\n"

            # ── analyze ────────────────────────────────────────────────
            elif step.type == "analyze":
                context_joined = "\n\n---\n\n".join(context_chunks)
                prompt = (
                    f"User question: {user_message}\n\n"
                    f"Information gathered:\n{context_joined}\n\n"
                    f"Task: {step.description}\n\n"
                    "Provide a focused, evidence-based analysis."
                )
                analysis = await asyncio.to_thread(
                    self._client.generate_text,
                    prompt,
                    "You are an expert analyst. Be precise, cite evidence, avoid stating audience type.",
                    0.4,
                )
                context_chunks.append(f"[Analysis]\n{analysis}")
                yield f"\n*🔍 Analysis complete ({len(analysis.split())} words).*\n"

            # ── summarize ──────────────────────────────────────────────
            elif step.type == "summarize":
                context_joined = "\n\n---\n\n".join(context_chunks)
                prompt = (
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
                yield f"\n[Unknown step type: {step.type}]\n"
