from __future__ import annotations

import asyncio
import json

import pytest

from engine.chat.modal_sandbox import ModalSandboxExecutor
from engine.chat.sandbox_workspace import SandboxCommand, SandboxProfile, SandboxWorkspaceManager
from engine.chat.modal_tools import ModalToolExecutor
from engine.chat.execution import RoutedChatToolExecutor
from engine.tools.contracts import ChatToolInvocation


class AioCall:
    def __init__(self, function):
        self._function = function

    async def aio(self, *args, **kwargs):
        return self._function(*args, **kwargs)


class FakeStream:
    def __init__(self, content):
        self.read = AioCall(lambda: content)


class FakeProcess:
    def __init__(self, stdout="ok", stderr="", code=0):
        self.stdout = FakeStream(stdout)
        self.stderr = FakeStream(stderr)
        self.wait = AioCall(lambda: code)


class FakeSandbox:
    def __init__(self):
        self.commands = []
        self.exec = AioCall(self._exec)
        self.terminate = AioCall(lambda: None)
        self.files = {}
        self.object_id = "sb-test"
        self.filesystem = type("Filesystem", (), {})()
        self.filesystem.make_directory = AioCall(lambda *_args, **_kwargs: None)
        self.filesystem.write_text = AioCall(
            lambda content, path: self.files.__setitem__(path, content)
        )
        self.filesystem.read_text = AioCall(lambda path: self.files[path])
        self.filesystem.list_files = AioCall(lambda _path: [])
        self.filesystem.stat = AioCall(lambda path: type("Info", (), {
            "type": type("Kind", (), {"value": "file"})(),
            "size": len(self.files[path]),
        })())
        self.detach = AioCall(lambda: None)
        self.poll = AioCall(lambda: None)

    def _exec(self, *args, **kwargs):
        self.commands.append((args, kwargs))
        return FakeProcess(stdout="repository output")

def test_repository_inspection_uses_no_secret_limited_network_sandbox() -> None:
    captured = {}
    sandbox = FakeSandbox()
    app = object()

    async def factory(**kwargs):
        captured.update(kwargs)
        return sandbox

    async def app_resolver():
        return app

    result = asyncio.run(
        ModalSandboxExecutor(sandbox_factory=factory, app_resolver=app_resolver).execute(
            ChatToolInvocation(
                run_id="run_1",
                skill_id="repository_inspection",
                tool_name="repository_inspection",
                query="inspect files",
                arguments={
                    "repository_url": "https://github.com/openai/openai-python",
                    "operations": ["files"],
                },
                timeout_seconds=60,
            )
        )
    )

    assert result.error is None
    assert captured["outbound_domain_allowlist"] == [
        "github.com", "*.github.com", "githubusercontent.com", "*.githubusercontent.com",
    ]
    assert "secrets" not in captured
    assert captured["cpu"] == (1.0, 4.0)
    assert captured["memory"] == (2048, 8192)
    # The sandbox carries its environment via the associated app; the deprecated
    # environment_name= argument must no longer be passed to Sandbox.create.
    assert captured["app"] is app
    assert "environment_name" not in captured
    assert sandbox.commands[0][0][:3] == ("git", "clone", "--depth")


def test_trusted_function_executor_rejects_sandbox_tool_before_function_lookup() -> None:
    looked_up = False

    def lookup():
        nonlocal looked_up
        looked_up = True
        raise AssertionError("must not dispatch")

    invocation = ChatToolInvocation(
        run_id="run_1",
        skill_id="repository_inspection",
        tool_name="repository_inspection",
        query="inspect",
        arguments={"repository_url": "https://github.com/openai/openai-python", "operations": ["files"]},
        timeout_seconds=60,
    )
    try:
        asyncio.run(ModalToolExecutor(function_lookup=lookup).execute(invocation))
    except ValueError as exc:
        assert "not a trusted" in str(exc)
    else:
        raise AssertionError("expected executor boundary rejection")
    assert looked_up is False


def test_code_execution_writes_files_and_runs_without_network_or_secrets() -> None:
    captured = {}
    sandbox = FakeSandbox()

    async def factory(**kwargs):
        captured.update(kwargs)
        return sandbox

    async def app_resolver():
        return object()

    result = asyncio.run(ModalSandboxExecutor(sandbox_factory=factory, app_resolver=app_resolver).execute(
        ChatToolInvocation(
            run_id="run_1",
            skill_id="code_execution",
            tool_name="code_execution",
            query="write and run python",
            arguments={"files": {"main.py": "print(6 * 7)"}, "command": ["python", "main.py"]},
            timeout_seconds=60,
        )
    ))

    assert result.error is None
    assert captured["block_network"] is True
    assert "secrets" not in captured
    assert "environment_name" not in captured
    assert sandbox.files["/workspace/main.py"] == "print(6 * 7)"
    assert sandbox.commands[-1][0] == ("python", "main.py")


def test_stateful_workspace_reuses_files_and_closes_explicitly() -> None:
    sandbox = FakeSandbox()

    async def factory(**_kwargs):
        return sandbox

    async def app_resolver():
        return object()

    async def scenario() -> None:
        executor = ModalSandboxExecutor(sandbox_factory=factory, app_resolver=app_resolver)
        create = await executor.execute(ChatToolInvocation(
            run_id="run_stateful", skill_id="sandbox_workspace", tool_name="sandbox_create",
            query="create workspace", arguments={"purpose": "code", "profile": "code"},
            timeout_seconds=60,
        ))
        workspace_id = json.loads(create.content)["workspace_id"]
        await executor.execute(ChatToolInvocation(
            run_id="run_stateful", skill_id="sandbox_workspace", tool_name="sandbox_write",
            query="write file", arguments={"workspace_id": workspace_id, "files": {"state.txt": "kept"}},
            timeout_seconds=60,
        ))
        read = await executor.execute(ChatToolInvocation(
            run_id="run_stateful", skill_id="sandbox_workspace", tool_name="sandbox_read",
            query="read file", arguments={"workspace_id": workspace_id, "path": "state.txt"},
            timeout_seconds=60,
        ))
        assert read.content == "kept"
        await executor.execute(ChatToolInvocation(
            run_id="run_stateful", skill_id="sandbox_workspace", tool_name="sandbox_close",
            query="close", arguments={"workspace_id": workspace_id}, timeout_seconds=60,
        ))

    asyncio.run(scenario())


def test_workspace_state_reconnects_by_private_modal_object_id() -> None:
    sandbox = FakeSandbox()

    async def factory(**_kwargs):
        return sandbox

    async def app_resolver():
        return object()

    looked_up = []

    async def lookup(object_id):
        looked_up.append(object_id)
        return sandbox

    async def scenario() -> None:
        original = SandboxWorkspaceManager(sandbox_factory=factory, app_resolver=app_resolver)
        descriptor = await original.create(
            run_id="research-run:1", purpose="code", profile=SandboxProfile.CODE,
        )
        state = original.private_states()
        restored = SandboxWorkspaceManager(
            sandbox_factory=factory, sandbox_lookup=lookup, app_resolver=app_resolver,
        )
        await restored.restore_states(state)
        assert looked_up == ["sb-test"]
        assert restored.status(descriptor.workspace_id)["status"] == "ready"

    asyncio.run(scenario())


def test_workspace_restore_preserves_command_budget_and_pending_changes() -> None:
    sandbox = FakeSandbox()

    async def factory(**_kwargs):
        return sandbox

    async def app_resolver():
        return object()

    async def lookup(_object_id):
        return sandbox

    async def scenario() -> None:
        original = SandboxWorkspaceManager(sandbox_factory=factory, app_resolver=app_resolver)
        descriptor = await original.create(
            run_id="research-run:budget", purpose="code", profile=SandboxProfile.CODE,
            command_limit=2,
        )
        await original.exec(SandboxCommand(descriptor.workspace_id, ("python", "-V")))
        await original.write_files(descriptor.workspace_id, {"changed.txt": "kept"})

        restored = SandboxWorkspaceManager(
            sandbox_factory=factory, sandbox_lookup=lookup, app_resolver=app_resolver,
        )
        await restored.restore_states(original.private_states())
        status = restored.status(descriptor.workspace_id)
        assert status["commands_used"] == 1
        final = await restored.exec(SandboxCommand(descriptor.workspace_id, ("python", "-V")))
        assert final.changed_files == ("changed.txt",)
        with pytest.raises(ValueError, match="budget exhausted"):
            await restored.exec(SandboxCommand(descriptor.workspace_id, ("python", "-V")))

    asyncio.run(scenario())


def test_failed_termination_keeps_private_cleanup_handle() -> None:
    sandbox = FakeSandbox()
    sandbox.terminate = AioCall(lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))

    async def factory(**_kwargs):
        return sandbox

    async def app_resolver():
        return object()

    async def scenario() -> None:
        manager = SandboxWorkspaceManager(sandbox_factory=factory, app_resolver=app_resolver)
        descriptor = await manager.create(
            run_id="cleanup", purpose="code", profile=SandboxProfile.CODE,
        )
        with pytest.raises(RuntimeError, match="offline"):
            await manager.close(descriptor.workspace_id)
        state = manager.private_states()
        assert state[0]["descriptor"]["workspace_id"] == descriptor.workspace_id
        assert state[0]["modal_object_id"] == "sb-test"

    asyncio.run(scenario())


def test_routed_executor_closes_both_tiers_when_one_cleanup_fails() -> None:
    closed = []

    class Executor:
        def __init__(self, name, *, fail=False):
            self.name = name
            self.fail = fail

        async def aclose(self):
            closed.append(self.name)
            if self.fail:
                raise RuntimeError(f"{self.name} failed")

    async def scenario() -> None:
        executor = RoutedChatToolExecutor(
            trusted=Executor("trusted", fail=True),
            sandbox=Executor("sandbox"),
        )
        with pytest.raises(ExceptionGroup, match="failed to close"):
            await executor.aclose()
        assert closed == ["trusted", "sandbox"]

    asyncio.run(scenario())


def test_workspace_enforces_path_and_command_budgets_and_reports_terminal_state() -> None:
    sandbox = FakeSandbox()
    reported = []

    async def factory(**_kwargs):
        return sandbox

    async def app_resolver():
        return object()

    async def state_reporter(states):
        reported.append(states)

    async def scenario() -> None:
        manager = SandboxWorkspaceManager(
            sandbox_factory=factory,
            app_resolver=app_resolver,
            state_reporter=state_reporter,
        )
        descriptor = await manager.create(
            run_id="budgeted", purpose="code", profile=SandboxProfile.CODE,
            command_limit=1,
        )
        with pytest.raises(ValueError, match="under /workspace"):
            await manager.read_text(descriptor.workspace_id, "/etc/passwd")
        first = await manager.exec(SandboxCommand(descriptor.workspace_id, ("python", "-V")))
        assert first.exit_code == 0
        with pytest.raises(ValueError, match="budget exhausted"):
            await manager.exec(SandboxCommand(descriptor.workspace_id, ("python", "-V")))
        await manager.close(descriptor.workspace_id)
        assert reported[0]
        assert reported[-1] == []

    asyncio.run(scenario())
