"""Policy adapter for stateful Modal Sandbox tools and compatibility wrappers."""
from __future__ import annotations

import re
from typing import Any

from engine.chat.modal_tools import ChatToolResult
from engine.chat.sandbox_workspace import (
    SandboxCommand,
    SandboxProfile,
    SandboxWorkspaceManager,
    result_content,
)
from engine.chat.effort import get_chat_effort_profile
from engine.tools import TOOL_REGISTRY
from engine.tools.contracts import ChatToolInvocation, validate_chat_tool_invocation


_WORKSPACE_TOOLS = {
    "sandbox_create", "sandbox_exec", "sandbox_list", "sandbox_read",
    "sandbox_write", "sandbox_status", "sandbox_close",
}


class ModalSandboxExecutor:
    """No-secret executor owning stateful workspaces for one task or run."""

    def __init__(
        self,
        sandbox_factory=None,
        app_resolver=None,
        workspace_manager: SandboxWorkspaceManager | None = None,
    ) -> None:
        self._manager = workspace_manager or SandboxWorkspaceManager(
            sandbox_factory=sandbox_factory,
            app_resolver=app_resolver,
        )

    @property
    def workspace_manager(self) -> SandboxWorkspaceManager:
        return self._manager

    async def execute(self, invocation: ChatToolInvocation) -> ChatToolResult:
        validated = validate_chat_tool_invocation(invocation)
        if TOOL_REGISTRY.descriptor(validated.tool_name).execution_kind != "sandbox":
            raise ValueError(f"{validated.tool_name} is not a Modal Sandbox operation")
        if validated.tool_name in _WORKSPACE_TOOLS:
            return await self._workspace_operation(validated)
        if validated.tool_name == "repository_inspection":
            return await self._inspect_repository(validated)
        if validated.tool_name == "dataset_analysis":
            return await self._analyze_dataset(validated)
        if validated.tool_name == "code_execution":
            return await self._execute_code(validated)
        raise ValueError(f"Unsupported sandbox tool: {validated.tool_name}")

    async def _workspace_operation(self, invocation) -> ChatToolResult:
        arguments = invocation.arguments
        if invocation.tool_name == "sandbox_create":
            descriptor = await self._manager.create(
                run_id=invocation.run_id,
                purpose=arguments["purpose"],
                profile=SandboxProfile(arguments["profile"]),
                repository_url=arguments.get("repository_url"),
                ref=arguments.get("ref"),
                command_limit=get_chat_effort_profile(invocation.effort).max_tool_actions,
            )
            return ChatToolResult(result_content(descriptor.public_dict()), [], 1.0, None)
        workspace_id = arguments["workspace_id"]
        if invocation.tool_name == "sandbox_exec":
            result = await self._manager.exec(SandboxCommand(
                workspace_id=workspace_id,
                argv=tuple(arguments["argv"]),
                workdir=arguments.get("workdir", "/workspace"),
                timeout_seconds=min(arguments.get("command_timeout_seconds", 60), invocation.timeout_seconds),
            ))
            error = None if result.exit_code == 0 else f"command exited with code {result.exit_code}"
            return ChatToolResult(
                result_content(result.as_dict()), [], 1.0 if error is None else 0.0, error, executed=True
            )
        if invocation.tool_name == "sandbox_list":
            entries = await self._manager.list_files(workspace_id, arguments.get("path", "/workspace"))
            return ChatToolResult(result_content({"entries": entries}), [], 1.0, None, executed=True)
        if invocation.tool_name == "sandbox_read":
            content = await self._manager.read_text(
                workspace_id, arguments["path"],
                offset=arguments.get("offset", 0), limit=arguments.get("limit", 50_000),
            )
            return ChatToolResult(content, [], 1.0, None, executed=True)
        if invocation.tool_name == "sandbox_write":
            written = await self._manager.write_files(workspace_id, arguments["files"])
            return ChatToolResult(result_content({"written": written}), [], 1.0, None)
        if invocation.tool_name == "sandbox_status":
            return ChatToolResult(result_content(self._manager.status(workspace_id)), [], 1.0, None)
        if invocation.tool_name == "sandbox_close":
            await self._manager.close(workspace_id)
            return ChatToolResult(result_content({"workspace_id": workspace_id, "status": "closed"}), [], 1.0, None)
        raise ValueError(f"Unsupported workspace operation: {invocation.tool_name}")

    async def _inspect_repository(self, invocation) -> ChatToolResult:
        arguments = invocation.arguments
        descriptor = await self._manager.create(
            run_id=invocation.run_id,
            purpose="repository",
            profile=SandboxProfile.REPOSITORY_BUILD if "tests" in arguments["operations"] else SandboxProfile.REPOSITORY,
            repository_url=arguments["repository_url"],
            ref=arguments.get("ref"),
            command_limit=get_chat_effort_profile(invocation.effort).max_tool_actions,
        )
        sections: list[str] = []
        failed_operations: list[str] = []
        operation_results: list[dict[str, Any]] = []
        for operation in arguments["operations"]:
            result = await self._manager.exec(SandboxCommand(
                descriptor.workspace_id,
                tuple(_repository_command(operation)),
                "/workspace/repository",
                min(120, invocation.timeout_seconds),
            ))
            sections.append(
                f"## {operation} (exit={result.exit_code})\n{result.stdout}\n{result.stderr}".strip()
            )
            if result.exit_code != 0:
                failed_operations.append(operation)
            operation_results.append({
                "operation": operation,
                "exit_code": result.exit_code,
                "elapsed_seconds": result.elapsed_seconds,
                "truncated": result.truncated,
                "changed_files": list(result.changed_files),
            })
        content = "\n\n".join(sections)
        commit = descriptor.commit_sha or arguments.get("ref") or "HEAD"
        sources = [{
            "title": arguments["repository_url"].rsplit("/", 1)[-1],
            "url": f"{arguments['repository_url']}/tree/{commit}",
            "snippet": content[:500],
            "date": None,
            "source_type": "repository",
            "credibility_base": 0.85,
            "metadata": {
                "commit_sha": descriptor.commit_sha,
                "workspace_profile": descriptor.profile.value,
                "operation_results": operation_results,
            },
        }]
        for path, excerpt in _file_excerpts(content):
            sources.append({
                "title": path,
                "url": f"{arguments['repository_url']}/blob/{commit}/{path}",
                "snippet": excerpt[:2_000],
                "date": None,
                "source_type": "repository_file",
                "credibility_base": 0.9,
                "metadata": {"commit_sha": descriptor.commit_sha, "path": path},
            })
        return ChatToolResult(
            content=content,
            sources=sources,
            credibility_base=0.85,
            error=(
                f"repository inspection failed for: {', '.join(failed_operations)}"
                if len(failed_operations) == len(arguments["operations"])
                else None
            ),
            executed=True,
        )

    async def _analyze_dataset(self, invocation) -> ChatToolResult:
        descriptor = await self._manager.create(
            run_id=invocation.run_id, purpose="dataset", profile=SandboxProfile.DATA,
            command_limit=get_chat_effort_profile(invocation.effort).max_tool_actions,
        )
        await self._manager.write_files(descriptor.workspace_id, {
            "input.csv": invocation.arguments["dataset_csv"],
            "analysis.py": invocation.arguments["python_code"],
        })
        result = await self._manager.exec(SandboxCommand(
            descriptor.workspace_id,
            ("python", "analysis.py"),
            "/workspace",
            invocation.timeout_seconds,
        ))
        error = None if result.exit_code == 0 else f"dataset analysis exited with code {result.exit_code}"
        content = result_content(result.as_dict())
        return ChatToolResult(content, [{
            "title": "Validated dataset computation",
            "url": "",
            "snippet": content[:2_000],
            "source_type": "sandbox_execution",
            "credibility_base": 1.0,
            "metadata": result.provenance,
        }], 1.0 if error is None else 0.0, error, executed=True)

    async def _execute_code(self, invocation) -> ChatToolResult:
        descriptor = await self._manager.create(
            run_id=invocation.run_id, purpose="code", profile=SandboxProfile.CODE,
            command_limit=get_chat_effort_profile(invocation.effort).max_tool_actions,
        )
        await self._manager.write_files(descriptor.workspace_id, invocation.arguments["files"])
        result = await self._manager.exec(SandboxCommand(
            descriptor.workspace_id,
            tuple(invocation.arguments["command"]),
            "/workspace",
            invocation.timeout_seconds,
        ))
        error = None if result.exit_code == 0 else f"code execution exited with code {result.exit_code}"
        content = result_content(result.as_dict())
        return ChatToolResult(content, [{
            "title": "Validated isolated code execution",
            "url": "",
            "snippet": content[:2_000],
            "source_type": "sandbox_execution",
            "credibility_base": 1.0,
            "metadata": result.provenance,
        }], 1.0 if error is None else 0.0, error, executed=True)

    async def aclose(self) -> None:
        await self._manager.aclose()

    def workspace_states(self) -> list[dict[str, Any]]:
        return self._manager.private_states()

    async def restore_workspace_states(self, states: list[dict[str, Any]]) -> None:
        await self._manager.restore_states(states)


def _repository_command(operation: str) -> list[str]:
    if operation == "files":
        return [
            "bash", "-lc",
            "rg --files -g '!node_modules' -g '!vendor' | head -n 1000; "
            "for f in README.md README.rst pyproject.toml package.json Cargo.toml go.mod; do "
            "if [ -f \"$f\" ]; then printf '\\n===== FILE: %s =====\\n' \"$f\"; "
            "sed -n '1,240p' \"$f\"; fi; done",
        ]
    if operation == "git_summary":
        return ["git", "log", "-5", "--oneline", "--decorate"]
    if operation == "tests":
        return ["python", "-m", "pytest", "-q"]
    if operation == "static_analysis":
        return ["ruff", "check", ".", "--output-format", "concise"]
    raise ValueError(f"Unknown repository inspection operation: {operation}")


def _file_excerpts(content: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^===== FILE: ([^\n]+) =====$", content, re.MULTILINE))
    excerpts: list[tuple[str, str]] = []
    for index, match in enumerate(matches[:12]):
        path = match.group(1).strip()
        if path.startswith("/") or ".." in path.split("/"):
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        excerpts.append((path, content[match.end():end].strip()))
    return excerpts
