from __future__ import annotations

import re
from enum import StrEnum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .caps import RunCaps


class ResearchNodeStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    ANSWERED = "answered"
    QA_FAILED = "qa_failed"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class ResearchNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    question: str = Field(min_length=1, max_length=4_000)
    rationale: str = ""
    level: int = Field(ge=0, le=4)
    parent_id: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    section_id: str = Field(min_length=1)
    acceptance_criteria: list[str] = Field(default_factory=list)
    expected_evidence: list[str] = Field(default_factory=list)
    requires_fresh: bool = False
    status: ResearchNodeStatus = ResearchNodeStatus.PENDING
    tool_calls_used: int = 0
    attempts: int = Field(default=0, ge=0)
    last_error: str | None = None
    answer_id: str | None = None
    answer: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    source_records: list[dict] = Field(default_factory=list)
    unresolved_gaps: list[str] = Field(default_factory=list)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @property
    def question_key(self) -> str:
        return re.sub(r"[^a-z0-9]+", " ", self.question.lower()).strip()


class ResearchDAG(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: dict[str, ResearchNode] = Field(default_factory=dict)

    def add_node(self, node: ResearchNode, caps: RunCaps) -> None:
        if len(self.nodes) >= caps.max_nodes:
            raise ValueError("DAG node cap reached")
        if node.node_id in self.nodes:
            raise ValueError(f"duplicate node id: {node.node_id}")
        if node.level > caps.max_dag_depth:
            raise ValueError("DAG depth cap reached")
        existing_keys = {n.question_key for n in self.nodes.values()}
        if node.question_key in existing_keys:
            raise ValueError("duplicate normalized research question")
        missing = set(node.depends_on) - self.nodes.keys()
        if missing:
            raise ValueError(f"missing dependencies: {sorted(missing)}")
        if node.parent_id is not None and node.parent_id not in self.nodes:
            raise ValueError(f"missing parent: {node.parent_id}")
        self.nodes[node.node_id] = node
        try:
            self.validate_acyclic()
        except Exception:
            self.nodes.pop(node.node_id, None)
            raise

    def add_suggestions(self, section_id: str, suggestions: Iterable[ResearchNode], caps: RunCaps) -> tuple[list[str], list[str]]:
        accepted: list[str] = []
        rejected: list[str] = []
        count = 0
        for node in suggestions:
            if node.section_id != section_id or count >= caps.max_qa_suggestions_per_section:
                rejected.append(node.node_id)
                continue
            try:
                self.add_node(node, caps)
            except ValueError:
                rejected.append(node.node_id)
                continue
            accepted.append(node.node_id)
            count += 1
        return accepted, rejected

    def validate_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("research DAG contains a cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            node = self.nodes[node_id]
            for dependency in node.depends_on:
                if dependency not in self.nodes:
                    raise ValueError(f"missing dependency: {dependency}")
                visit(dependency)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in self.nodes:
            visit(node_id)

    def ready_nodes(self) -> list[ResearchNode]:
        return [
            node for node in self.nodes.values()
            if node.status == ResearchNodeStatus.PENDING
            and all(
                self.nodes[dep].status in {
                    ResearchNodeStatus.ANSWERED,
                    ResearchNodeStatus.PASSED,
                    ResearchNodeStatus.QA_FAILED,
                }
                for dep in node.depends_on
            )
        ]

    def recover_interrupted_nodes(self, *, max_attempts: int = 2) -> list[str]:
        """Make checkpoint-resume safe after a worker dies mid-node."""
        recovered: list[str] = []
        for node in self.nodes.values():
            if node.status != ResearchNodeStatus.RUNNING:
                continue
            if node.attempts < max_attempts:
                node.status = ResearchNodeStatus.PENDING
                node.last_error = "worker interrupted; retrying from checkpoint"
                recovered.append(node.node_id)
            else:
                node.status = ResearchNodeStatus.FAILED
                node.last_error = "worker interrupted after retry budget was exhausted"
        return recovered

    def unresolved_nodes(self) -> list[ResearchNode]:
        return [n for n in self.nodes.values() if n.status not in {ResearchNodeStatus.PASSED, ResearchNodeStatus.CANCELLED}]
