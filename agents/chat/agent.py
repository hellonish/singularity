"""
ChatAgent — top-level façade for the dual-mode chat agent.

Supports runtime model switching via .set_model(model_id).

Usage:
    from agents.chat import ChatAgent
    agent = ChatAgent()
    async for chunk in agent.chat("What is transformer attention?"):
        print(chunk, end="", flush=True)
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Ensure project root on path
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents.chat.thinker import Thinker, ThinkPlan
from agents.chat.executor import ChatModeExecutor
from agents.chat.models import (
    AVAILABLE_MODELS, DEFAULT_MODEL_ID, make_client, get_model_info
)


# ---------------------------------------------------------------------------
# ChatAgent
# ---------------------------------------------------------------------------

class ChatAgent:
    """
    Dual-mode AI agent.

    Chat Mode    — lightweight: Thinker plans 1-5 steps → ChatModeExecutor runs them.
    Research Mode — heavy: Thinker plans 5-10 steps → delegates to run_pipeline().

    Args:
        model_id:  Initial response model (defaults to grok-3-mini).
        extended:  If True, thinker may use research mode + more steps.
    """

    # Thinker always uses grok-3-mini (fast, structured output)
    _THINKER_MODEL = "grok-3-mini"

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        extended: bool = False,
    ) -> None:
        self._model_id = model_id
        self.extended  = extended

        # Thinker is always grok-3-mini (structured planning)
        from llm.grok import GrokClient
        self._thinker_client  = GrokClient(model_name=self._THINKER_MODEL)
        self._thinker         = Thinker(self._thinker_client)

        # Response client — switchable
        self._response_client = make_client(model_id)
        self._executor        = ChatModeExecutor(self._response_client)

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    @property
    def model_id(self) -> str:
        return self._model_id

    def set_model(self, model_id: str) -> None:
        """Switch the response model at runtime."""
        self._model_id        = model_id
        self._response_client = make_client(model_id)
        self._executor        = ChatModeExecutor(self._response_client)
        logger.info("Model switched to: %s", model_id)

    # ------------------------------------------------------------------
    # Think
    # ------------------------------------------------------------------

    def think(
        self,
        message: str,
        history: list[dict[str, str]],
    ) -> ThinkPlan:
        """
        Synchronous — returns the ThinkPlan for the given message.
        """
        return self._thinker.think(
            message=message,
            history=history,
            extended=self.extended,
        )

    # ------------------------------------------------------------------
    # Chat mode
    # ------------------------------------------------------------------

    async def run_chat_mode(
        self,
        plan: ThinkPlan,
        message: str,
        history: list[dict[str, str]],
    ) -> AsyncGenerator[str, None]:
        """Execute chat mode: streams response chunks."""
        async for chunk in self._executor.execute(plan, message, history):
            yield chunk

    # ------------------------------------------------------------------
    # Research mode
    # ------------------------------------------------------------------

    async def run_research_mode(
        self,
        plan: ThinkPlan,
        message: str,
    ) -> str:
        """Execute research mode via the full run_pipeline(). Returns Markdown."""
        from agents.orchestrator.pipeline import run_pipeline

        strength = max(1, min(10, plan.strength))
        audience = plan.audience or "practitioner"

        logger.info("[Research Mode] strength=%d audience=%s", strength, audience)

        report_md = await run_pipeline(
            query=message,
            strength=strength,
            audience=audience,
            output_language="en",
        )
        return report_md

    # ------------------------------------------------------------------
    # Unified entry point
    # ------------------------------------------------------------------

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[ThinkPlan, AsyncGenerator[str, None] | str]:
        """
        Full chat turn.

        Returns:
            (plan, result)
            - plan:   ThinkPlan (always returned for display)
            - result: AsyncGenerator[str] in chat mode, str in research mode
        """
        if history is None:
            history = []

        plan = await asyncio.to_thread(self.think, message, history)

        if plan.mode == "research":
            result = await self.run_research_mode(plan, message)
        else:
            result = self.run_chat_mode(plan, message, history)

        return plan, result
