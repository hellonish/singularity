"""Controlled Modal Sandbox execution for repository and dataset operations."""
from __future__ import annotations

import asyncio
import os
from typing import Any, Awaitable, Callable

import modal

from engine.chat.modal_tools import ChatToolResult, modal_environment_name
from engine.tools import TOOL_REGISTRY
from engine.tools.contracts import ChatToolInvocation, ValidatedChatToolInvocation, validate_chat_tool_invocation

_OUTPUT_LIMIT = 50_000

repository_sandbox_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install("pytest", "ruff")
)
dataset_sandbox_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("pandas", "numpy", "matplotlib", "scipy")
)
code_sandbox_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("pytest", "ruff")
)


def _sandbox_app_name() -> str:
    return os.getenv("SINGULARITY_MODAL_SANDBOX_APP", "singularity-chat-sandbox")


class ModalSandboxExecutor:
    """No-secret adapter for runtime-generated or user-provided execution."""

    def __init__(
        self,
        sandbox_factory: Callable[..., Any] | None = None,
        app_resolver: Callable[[], Awaitable[Any]] | None = None,
    ) -> None:
        self._sandbox_factory = sandbox_factory or modal.Sandbox.create.aio
        self._app_resolver = app_resolver or self._lookup_app
        self._app: Any | None = None
        self._app_lock = asyncio.Lock()

    async def _lookup_app(self) -> Any:
        # A Sandbox is created against an App, and the App carries the
        # environment. Passing environment_name= to Sandbox.create is deprecated
        # (Modal derives it from the associated app), so we resolve one app
        # handle and reuse it for every sandbox this executor spawns.
        return await modal.App.lookup.aio(
            _sandbox_app_name(),
            environment_name=modal_environment_name(),
            create_if_missing=True,
        )

    async def _get_app(self) -> Any:
        if self._app is not None:
            return self._app
        async with self._app_lock:
            if self._app is None:
                self._app = await self._app_resolver()
            return self._app

    async def execute(self, invocation: ChatToolInvocation) -> ChatToolResult:
        validated = validate_chat_tool_invocation(invocation)
        if TOOL_REGISTRY.descriptor(validated.tool_name).execution_kind != "sandbox":
            raise ValueError(f"{validated.tool_name} is not a Modal Sandbox operation")
        async with asyncio.timeout(validated.timeout_seconds):
            if validated.tool_name == "repository_inspection":
                return await self._inspect_repository(validated)
            if validated.tool_name == "dataset_analysis":
                return await self._analyze_dataset(validated)
            if validated.tool_name == "code_execution":
                return await self._execute_code(validated)
        raise ValueError(f"Unsupported sandbox tool: {validated.tool_name}")

    async def _inspect_repository(self, invocation: ValidatedChatToolInvocation) -> ChatToolResult:
        sandbox = await self._sandbox_factory(
            app=await self._get_app(),
            image=repository_sandbox_image,
            timeout=invocation.timeout_seconds,
            idle_timeout=60,
            cpu=1.0,
            memory=2048,
            outbound_domain_allowlist=["github.com"],
        )
        try:
            arguments = invocation.arguments
            clone = ["git", "clone", "--depth", "1"]
            if arguments.get("ref"):
                clone.extend(["--branch", arguments["ref"]])
            clone.extend([arguments["repository_url"], "/workspace/repository"])
            clone_output, clone_code = await _exec(sandbox, clone, timeout=min(90, invocation.timeout_seconds))
            if clone_code != 0:
                return ChatToolResult("", [], 0.0, f"repository clone failed: {clone_output[:1000]}")

            sections = []
            for operation in arguments["operations"]:
                command = _repository_command(operation)
                output, return_code = await _exec(
                    sandbox,
                    command,
                    workdir="/workspace/repository",
                    timeout=min(120, invocation.timeout_seconds),
                )
                sections.append(f"## {operation} (exit={return_code})\n{output}")
            content = "\n\n".join(sections)[:_OUTPUT_LIMIT]
            return ChatToolResult(
                content=content,
                sources=[{
                    "title": arguments["repository_url"].rsplit("/", 1)[-1],
                    "url": arguments["repository_url"],
                    "snippet": content[:500],
                    "date": None,
                    "source_type": "repository",
                    "credibility_base": 0.70,
                }],
                credibility_base=0.70,
                error=None,
            )
        finally:
            await sandbox.terminate.aio()

    async def _analyze_dataset(self, invocation: ValidatedChatToolInvocation) -> ChatToolResult:
        sandbox = await self._sandbox_factory(
            app=await self._get_app(),
            image=dataset_sandbox_image,
            timeout=invocation.timeout_seconds,
            idle_timeout=60,
            cpu=1.0,
            memory=2048,
            block_network=True,
        )
        try:
            dataset_file = await sandbox.open.aio("/tmp/input.csv", "w")
            await dataset_file.write.aio(invocation.arguments["dataset_csv"])
            await dataset_file.close.aio()
            code_file = await sandbox.open.aio("/tmp/analysis.py", "w")
            await code_file.write.aio(invocation.arguments["python_code"])
            await code_file.close.aio()
            output, return_code = await _exec(
                sandbox,
                ["python", "/tmp/analysis.py"],
                workdir="/tmp",
                timeout=invocation.timeout_seconds,
                env={"SINGULARITY_DATASET_PATH": "/tmp/input.csv", "MPLBACKEND": "Agg"},
            )
            error = None if return_code == 0 else f"dataset analysis exited with code {return_code}"
            return ChatToolResult(output[:_OUTPUT_LIMIT], [], 1.0 if error is None else 0.0, error)
        finally:
            await sandbox.terminate.aio()

    async def _execute_code(self, invocation: ValidatedChatToolInvocation) -> ChatToolResult:
        sandbox = await self._sandbox_factory(
            app=await self._get_app(),
            image=code_sandbox_image,
            timeout=invocation.timeout_seconds,
            idle_timeout=60,
            cpu=2.0,
            memory=4096,
            block_network=True,
        )
        try:
            for relative_path, content in invocation.arguments["files"].items():
                target = f"/workspace/{relative_path}"
                parent = target.rsplit("/", 1)[0]
                if parent != "/workspace":
                    await _exec(sandbox, ["mkdir", "-p", parent], timeout=30)
                handle = await sandbox.open.aio(target, "w")
                await handle.write.aio(content)
                await handle.close.aio()
            output, return_code = await _exec(
                sandbox,
                invocation.arguments["command"],
                workdir="/workspace",
                timeout=invocation.timeout_seconds,
                env={"PYTHONDONTWRITEBYTECODE": "1", "MPLBACKEND": "Agg"},
            )
            content = f"exit_code={return_code}\n{output}"[:_OUTPUT_LIMIT]
            error = None if return_code == 0 else f"code execution exited with code {return_code}"
            return ChatToolResult(content, [], 1.0 if error is None else 0.0, error)
        finally:
            await sandbox.terminate.aio()


async def _exec(sandbox, command: list[str], **kwargs) -> tuple[str, int]:
    process = await sandbox.exec.aio(*command, **kwargs)
    stdout, stderr = await asyncio.gather(process.stdout.read.aio(), process.stderr.read.aio())
    return_code = await process.wait.aio()
    combined = f"{stdout}\n{stderr}".strip()
    return combined[:_OUTPUT_LIMIT], int(return_code)


def _repository_command(operation: str) -> list[str]:
    if operation == "files":
        return [
            "python", "-c",
            "from itertools import islice; from pathlib import Path; print('\\n'.join(str(p) for p in islice((p for p in Path('.').rglob('*') if p.is_file()), 500)))",
        ]
    if operation == "git_summary":
        return ["git", "log", "-5", "--oneline", "--decorate"]
    if operation == "tests":
        return ["python", "-m", "pytest", "-q"]
    if operation == "static_analysis":
        return ["ruff", "check", ".", "--output-format", "concise"]
    raise ValueError(f"Unknown repository inspection operation: {operation}")
