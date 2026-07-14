from __future__ import annotations

import asyncio

from engine.chat.modal_sandbox import ModalSandboxExecutor
from engine.chat.modal_tools import ModalToolExecutor
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
        self.open = AioCall(self._open)

    def _exec(self, *args, **kwargs):
        self.commands.append((args, kwargs))
        return FakeProcess(stdout="repository output")

    def _open(self, path, mode):
        sandbox = self

        class File:
            write = AioCall(lambda content: sandbox.files.__setitem__(path, content))
            close = AioCall(lambda: None)

        return File()


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
    assert captured["outbound_domain_allowlist"] == ["github.com"]
    assert "secrets" not in captured
    assert captured["cpu"] == 1.0
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
