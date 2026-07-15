"""Descriptors for operations that must never execute as trusted Functions."""
from __future__ import annotations

from typing import ClassVar

from .base import ToolBase, ToolResult


class _SandboxOnlyTool(ToolBase):
    execution_kind: ClassVar = "sandbox"

    async def call(self, query: str, **kwargs) -> ToolResult:
        raise RuntimeError(f"{self.name} must be dispatched through ModalSandboxExecutor")


class RepositoryInspectionTool(_SandboxOnlyTool):
    name = "repository_inspection"
    description = "Clone a public GitHub repository and run controlled inspection, tests, or static analysis in a Modal Sandbox."
    skill_ids = ("repository_inspection",)


class DatasetAnalysisTool(_SandboxOnlyTool):
    name = "dataset_analysis"
    description = "Run generated Python analysis over an explicitly supplied CSV dataset in a network-blocked Modal Sandbox."
    skill_ids = ("dataset_analysis",)


class CodeExecutionTool(_SandboxOnlyTool):
    name = "code_execution"
    description = (
        "Write a bounded set of files in an isolated network-blocked Modal Sandbox, "
        "execute one argv-style command, and return stdout, stderr, and the exit code."
    )
    skill_ids = ("code_execution",)


class SandboxCreateTool(_SandboxOnlyTool):
    name = "sandbox_create"
    description = "Create or reuse a task-scoped stateful Modal Sandbox workspace selected by a policy profile."
    skill_ids = ("sandbox_workspace",)


class SandboxExecTool(_SandboxOnlyTool):
    name = "sandbox_exec"
    description = "Run one argv-style command in an existing stateful Sandbox workspace and return structured output."
    skill_ids = ("sandbox_workspace",)


class SandboxListTool(_SandboxOnlyTool):
    name = "sandbox_list"
    description = "List files under /workspace in an existing Sandbox without exposing Modal control identifiers."
    skill_ids = ("sandbox_workspace",)


class SandboxReadTool(_SandboxOnlyTool):
    name = "sandbox_read"
    description = "Read a bounded slice of a text file under /workspace in an existing Sandbox."
    skill_ids = ("sandbox_workspace",)


class SandboxWriteTool(_SandboxOnlyTool):
    name = "sandbox_write"
    description = "Write a bounded set of files under /workspace in an existing Sandbox."
    skill_ids = ("sandbox_workspace",)


class SandboxStatusTool(_SandboxOnlyTool):
    name = "sandbox_status"
    description = "Return the safe task-scoped status and provenance of an existing Sandbox workspace."
    skill_ids = ("sandbox_workspace",)


class SandboxCloseTool(_SandboxOnlyTool):
    name = "sandbox_close"
    description = "Terminate and detach an existing Sandbox workspace when it is no longer needed."
    skill_ids = ("sandbox_workspace",)
