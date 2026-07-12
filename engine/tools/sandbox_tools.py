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
