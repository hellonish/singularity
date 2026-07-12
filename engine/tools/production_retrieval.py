"""Descriptor for authorization-bound production vector retrieval."""
from __future__ import annotations

from typing import ClassVar

from .base import ToolBase, ToolResult


class ProductionRetrievalTool(ToolBase):
    name = "production_retrieval"
    description = "Retrieve authorized chat or report chunks through the API tenant boundary."
    skill_ids = ("production_retrieval",)
    execution_kind: ClassVar = "api_only"

    async def call(self, query: str, **kwargs) -> ToolResult:
        raise RuntimeError("production_retrieval is available only through authenticated API RetrievalService")
