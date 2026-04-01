"""Chunk and citation models shared between the vector store and citations packages."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentChunk:
    """A single chunk of text ingested into Qdrant for one research run.

    Produced by ``VectorStoreClient.ingest_text``; consumed by search results
    and report worker augmentation.
    """
    text:          str          # raw chunk text (≤ 512 tokens)
    source_url:    str
    source_title:  str
    credibility:   float        # 0–1, from ToolResult.credibility_base
    skill:         str          # retrieval skill that produced this chunk
    query:         str          # the sub-query that found this document
    run_id:        str
    chunk_index:   int          = 0
    id:            str          = field(default_factory=lambda: str(uuid.uuid4()))
    embedding:     list[float]  = field(default_factory=list)

    def to_qdrant_point(self) -> dict[str, Any]:
        """Return a qdrant-client PointStruct-compatible dict."""
        return {
            "id": self.id,
            "vector": self.embedding,
            "payload": {
                "run_id":       self.run_id,
                "skill":        self.skill,
                "query":        self.query,
                "source_url":   self.source_url,
                "source_title": self.source_title,
                "credibility":  self.credibility,
                "chunk_index":  self.chunk_index,
                "text":         self.text,
            },
        }

    @classmethod
    def from_qdrant_point(cls, point) -> "DocumentChunk":
        """Reconstruct a DocumentChunk from a Qdrant search result point."""
        p = point.payload or {}
        vec = getattr(point, "vector", None)
        return cls(
            id=str(point.id),
            text=p.get("text", ""),
            source_url=p.get("source_url", ""),
            source_title=p.get("source_title", "Unknown"),
            credibility=float(p.get("credibility", 0.5)),
            skill=p.get("skill", ""),
            query=p.get("query", ""),
            run_id=p.get("run_id", ""),
            chunk_index=int(p.get("chunk_index", 0)),
            embedding=list(vec) if vec else [],
        )


@dataclass
class CitationRecord:
    """A registered citation entry managed by CitationRegistry."""
    citation_id:        str    # e.g. "[Smith2024]"
    title:              str
    authors:            list[str]
    year:               str | None
    url:                str
    source_type:        str    # matches SourceType literals
    credibility_base:   float
    registered_by:      str    # skill name that found this source
    registered_at_slot: str    # output_slot of the node that registered it
