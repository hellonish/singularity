from __future__ import annotations

import os

import pytest

from engine.chat.agent_loop import sandbox_execution_observed
from engine.chat.modal_sandbox import ModalSandboxExecutor
from engine.chat.sandbox_workspace import (
    SandboxCommand,
    SandboxProfile,
    SandboxWorkspaceManager,
)
from engine.tools.contracts import ChatToolInvocation


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_modal_sandbox_shared_state_and_cleanup() -> None:
    if os.getenv("SINGULARITY_RUN_MODAL_SANDBOX_TESTS") != "1":
        pytest.skip("Set SINGULARITY_RUN_MODAL_SANDBOX_TESTS=1 for the live Sandbox smoke test")

    manager = SandboxWorkspaceManager()
    descriptor = await manager.create(
        run_id="live-sandbox-smoke",
        purpose="repository",
        profile=SandboxProfile.REPOSITORY,
        repository_url="https://github.com/octocat/Hello-World",
        command_limit=8,
    )
    try:
        entries = await manager.list_files(descriptor.workspace_id, "/workspace/repository")
        assert any(item["name"] == "README" for item in entries)
        assert "Hello World" in await manager.read_text(
            descriptor.workspace_id, "/workspace/repository/README"
        )
        await manager.write_files(descriptor.workspace_id, {"shared-state.txt": "persisted"})
        result = await manager.exec(SandboxCommand(
            descriptor.workspace_id,
            ("bash", "-lc", "test \"$(cat /workspace/shared-state.txt)\" = persisted"),
        ))
        assert result.exit_code == 0
        assert "shared-state.txt" in result.changed_files
    finally:
        await manager.close(descriptor.workspace_id)

    with pytest.raises(ValueError, match="unknown or closed"):
        manager.status(descriptor.workspace_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_code_level_failure_still_counts_as_evidence() -> None:
    if os.getenv("SINGULARITY_RUN_MODAL_SANDBOX_TESTS") != "1":
        pytest.skip("Set SINGULARITY_RUN_MODAL_SANDBOX_TESTS=1 for the live Sandbox smoke test")

    # A missing dependency makes the user's own program exit non-zero. The
    # Sandbox still ran it, so this is verifiable evidence the agent loop must
    # keep — not a reason to fail the whole turn closed.
    executor = ModalSandboxExecutor()
    invocation = ChatToolInvocation(
        run_id="live-code-level-failure",
        skill_id="code_execution",
        tool_name="code_execution",
        query="run a script that imports numpy",
        arguments={
            "files": {"main.py": "import numpy as np\nprint(np.array([1, 2, 3]).mean())\n"},
            "command": ["python", "main.py"],
        },
        effort="medium",
        timeout_seconds=60,
    )
    try:
        result = await executor.execute(invocation)
    finally:
        await executor.aclose()

    assert result.error is not None
    assert result.executed is True
    assert sandbox_execution_observed(result) is True
    assert "ModuleNotFoundError" in result.content
