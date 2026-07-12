"""Opt-in smoke test for the deployed trusted-tools Modal Function."""
from __future__ import annotations

import os

import pytest

from engine.chat.effort import ChatEffort, get_chat_effort_profile
from engine.chat.modal_tools import ModalToolExecutor
from engine.tools.contracts import ChatToolInvocation


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deployed_modal_function_executes_a_harmless_pubmed_search() -> None:
    if os.getenv("SINGULARITY_RUN_MODAL_TESTS") != "1":
        pytest.skip("Set SINGULARITY_RUN_MODAL_TESTS=1 after deploying the Modal tool app")

    profile = get_chat_effort_profile(ChatEffort.MEDIUM)
    result = await ModalToolExecutor().execute(
        ChatToolInvocation(
            run_id="modal-smoke-test",
            skill_id="medical_research",
            tool_name="pubmed",
            query="aspirin",
            arguments={"max_results": 1},
            effort=ChatEffort.MEDIUM,
            timeout_seconds=profile.timeout_seconds,
        )
    )

    assert result.error is None
    assert result.content
