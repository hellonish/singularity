"""Deliberate, low-cost live health check for terminal research dependencies.

Run only when requested:

    SINGULARITY_RUN_LIVE_RESEARCH_SMOKE=1 \
      .venv/bin/pytest -q tests/engine/test_live_research_smoke.py

The check makes no LLM completion request. It verifies the selected provider's
catalog endpoint and dispatches exactly one deployed Modal ``web_search`` call
with one requested result.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from engine.chat.effort import ChatEffort
from engine.chat.modal_tools import ModalToolExecutor
from engine.cli.settings import GlobalTerminalSettingsStore
from engine.cli.agents import ChatTerminalAgent
from engine.cli.models import TerminalSession
from engine.llm.providers import provider_for
from engine.llm.config import LLMRequestConfig
from engine.llm.structured import StructuredOutputSpec
from engine.tools.contracts import ChatToolInvocation


@pytest.mark.skipif(
    os.getenv("SINGULARITY_RUN_LIVE_RESEARCH_SMOKE") != "1",
    reason="Set SINGULARITY_RUN_LIVE_RESEARCH_SMOKE=1 to call the provider catalog and Modal once.",
)
@pytest.mark.integration
async def test_selected_provider_and_modal_research_tool_are_live() -> None:
    load_dotenv(Path(__file__).parents[2] / ".env")
    settings = GlobalTerminalSettingsStore().load()
    provider_name = settings.selected_provider
    api_key = settings.api_keys.get(provider_name, "")
    model_id = settings.models.get(provider_name, settings.model)
    assert api_key, f"No saved API key for {provider_name}"

    models = await provider_for(provider_name).list_models(api_key=api_key)
    assert model_id in {model.id for model in models}, f"Selected model is unavailable: {model_id}"

    executor = ModalToolExecutor()
    try:
        result = await executor.execute(ChatToolInvocation(
            run_id="live-research-smoke",
            skill_id="general_web_research",
            tool_name="web_search",
            query="OpenAI official site",
            arguments={"max_results": 1},
            effort=ChatEffort.INSTANT,
            timeout_seconds=20,
        ))
    finally:
        await executor.aclose()

    assert result.error is None, result.error
    assert len(result.sources) == 1


@pytest.mark.skipif(
    os.getenv("SINGULARITY_RUN_LIVE_LLM_SMOKE") != "1",
    reason="Set SINGULARITY_RUN_LIVE_LLM_SMOKE=1 to spend at most 128 completion tokens.",
)
@pytest.mark.integration
async def test_selected_model_returns_a_tiny_json_completion() -> None:
    """Probe the actual selected model without starting a research workflow."""
    settings = GlobalTerminalSettingsStore().load()
    provider_name = settings.selected_provider
    api_key = settings.api_keys[provider_name]
    model_id = settings.models.get(provider_name, settings.model)

    completion = await provider_for(provider_name).complete(
        api_key=api_key,
        config=LLMRequestConfig(
            provider=provider_name,
            credential_id="live-smoke",
            model_id=model_id,
            temperature=0,
            max_output_tokens=128,
        ),
        message='Return exactly this JSON object and nothing else: {"ok":true}',
        end_user_id="singularity-live-smoke",
        structured_output=StructuredOutputSpec.json_object(),
    )

    assert "ok" in completion.content.lower()


@pytest.mark.skipif(
    os.getenv("SINGULARITY_RUN_LIVE_CHAT_CHAIN") != "1",
    reason="Set SINGULARITY_RUN_LIVE_CHAT_CHAIN=1 for one search plus one capped answer.",
)
@pytest.mark.integration
async def test_live_current_chat_runs_search_before_answer() -> None:
    """Exercise routing, Modal, evidence injection, and selected-model output."""
    load_dotenv(Path(__file__).parents[2] / ".env")
    settings = GlobalTerminalSettingsStore().load()
    provider_name = settings.selected_provider
    model_id = settings.models.get(provider_name, settings.model)
    session = TerminalSession(
        api_key=settings.api_keys[provider_name],
        provider=provider_name,
        model_id=model_id,
        effort=ChatEffort.INSTANT,
    )
    outputs = [
        output
        async for output in ChatTerminalAgent().stream(
            message="What's going on with OpenAI? Give one current item and cite the source.",
            session=session,
        )
    ]

    assert any(output.kind == "tool_completed" for output in outputs)
    assert any(output.kind == "delta" and output.content for output in outputs)
