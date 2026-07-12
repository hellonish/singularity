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

    def _exec(self, *args, **kwargs):
        self.commands.append((args, kwargs))
        return FakeProcess(stdout="repository output")


def test_repository_inspection_uses_no_secret_limited_network_sandbox() -> None:
    captured = {}
    sandbox = FakeSandbox()

    async def factory(**kwargs):
        captured.update(kwargs)
        return sandbox

    result = asyncio.run(
        ModalSandboxExecutor(sandbox_factory=factory).execute(
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
