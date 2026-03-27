"""
Embedder — wraps sentence-transformers/all-MiniLM-L6-v2 (local, free, 384-dim).

Lazy-loads the model on first use so import doesn't pay the load cost.
Thread-safe: model is loaded once and reused across all calls.

Chunking strategy:
  - Split text at ~512-token boundaries (approximated as 2000 chars)
  - 64-token overlap (approximated as 256 chars) for continuity
"""
from __future__ import annotations

import re
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_CHUNK_SIZE_CHARS  = 2000   # ≈ 512 tokens
_CHUNK_OVERLAP_CHARS = 256  # ≈ 64 tokens
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_lock:  threading.Lock = threading.Lock()
_model: "SentenceTransformer | None" = None


def _get_model() -> "SentenceTransformer":
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(_MODEL_NAME)
    return _model


class Embedder:
    """Stateless helper — call embed() or chunk_and_embed()."""

    def embed(self, text: str) -> list[float]:
        """Embed a single string. Returns a 384-dim float list."""
        model = _get_model()
        vec = model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple strings in one forward pass."""
        model = _get_model()
        vecs = model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [v.tolist() for v in vecs]

    def chunk_text(self, text: str) -> list[str]:
        """
        Split text into overlapping windows of ~512 tokens.
        Uses character-count approximation to avoid tokeniser dependency.
        Splits on sentence boundaries where possible.
        """
        if len(text) <= _CHUNK_SIZE_CHARS:
            return [text]

        # Split on sentence boundaries first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= _CHUNK_SIZE_CHARS:
                current = (current + " " + sentence).strip()
            else:
                if current:
                    chunks.append(current)
                # Start new chunk with overlap from tail of previous
                overlap_start = max(0, len(current) - _CHUNK_OVERLAP_CHARS)
                current = (current[overlap_start:] + " " + sentence).strip()

        if current:
            chunks.append(current)

        return chunks if chunks else [text[:_CHUNK_SIZE_CHARS]]

    def chunk_and_embed(self, text: str) -> list[tuple[str, list[float]]]:
        """
        Returns list of (chunk_text, embedding) tuples.
        Batches all embeddings in one model call for efficiency.
        """
        chunks = self.chunk_text(text)
        embeddings = self.embed_batch(chunks)
        return list(zip(chunks, embeddings))
