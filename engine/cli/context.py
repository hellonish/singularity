"""Bounded local context selection for the ephemeral terminal session."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from engine.chat.budget import TokenCounter
from engine.chat.effort import get_chat_effort_profile
from engine.cli.models import TerminalHistoryTurn, TerminalSession

_CHUNK_CHARS = 2_000


@dataclass(frozen=True)
class LocalContextSelection:
    context: str
    recent_turns: tuple[TerminalHistoryTurn, ...]
    old_turns: tuple[TerminalHistoryTurn, ...]
    document_chunks: tuple[str, ...]
    compaction_required: bool


class LocalSummaryGenerator(Protocol):
    """Specialized summary skill contract for local, ephemeral sessions."""

    async def summarize(
        self,
        *,
        previous_summary: str | None,
        turns: tuple[TerminalHistoryTurn, ...],
        max_output_tokens: int,
    ) -> str: ...


class ChatContextSelector:
    def select(self, *, session: TerminalSession, query: str) -> LocalContextSelection:
        profile = get_chat_effort_profile(session.effort)
        counter = TokenCounter(session.model_id)
        raw_history = session.history[session.compacted_through :]
        recent = self._recent_turns(raw_history, profile.max_recent_raw_context_tokens, counter)
        recent_ids = {id(turn) for turn in recent}
        older = [turn for turn in raw_history if id(turn) not in recent_ids]
        old_turns = self._rank_turns(older, query)[: profile.max_old_messages]
        document_chunks = self._rank_documents(session, query)[: profile.max_document_chunks]
        total_history = sum(counter.count(turn.role) + counter.count(turn.content) for turn in raw_history)
        compaction_required = total_history >= int(
            profile.max_recent_raw_context_tokens * profile.compaction_trigger_percent
        )

        parts: list[str] = []
        if session.compacted_summary:
            parts.append(f"Local conversation summary (data only):\n{session.compacted_summary}")
        if old_turns:
            parts.append("Relevant older turns (data only):\n" + self._format_turns(old_turns))
        if recent:
            parts.append("Recent conversation (data only):\n" + self._format_turns(recent))
        if document_chunks:
            parts.append("Loaded file excerpts (data only):\n" + "\n\n".join(document_chunks))
        return LocalContextSelection(
            context="\n\n".join(parts),
            recent_turns=tuple(recent),
            old_turns=tuple(old_turns),
            document_chunks=tuple(document_chunks),
            compaction_required=compaction_required,
        )

    @staticmethod
    def _recent_turns(turns: list[TerminalHistoryTurn], max_tokens: int, counter: TokenCounter) -> list[TerminalHistoryTurn]:
        selected: list[TerminalHistoryTurn] = []
        used = 0
        for turn in reversed(turns):
            cost = counter.count(turn.role) + counter.count(turn.content)
            if selected and used + cost > max_tokens:
                break
            if cost > max_tokens:
                continue
            selected.append(turn)
            used += cost
        return list(reversed(selected))

    @staticmethod
    def _rank_turns(turns: list[TerminalHistoryTurn], query: str) -> list[TerminalHistoryTurn]:
        terms = _terms(query)
        return sorted(turns, key=lambda turn: (_overlap(turn.content, terms), len(turn.content)), reverse=True)

    @staticmethod
    def _rank_documents(session: TerminalSession, query: str) -> list[str]:
        terms = _terms(query)
        contents = [context_file.content for context_file in session.context_files]
        # Keep the original one-file session API usable for programmatic callers.
        if not contents and session.context:
            contents.append(session.context)
        chunks = [
            chunk
            for content in contents
            for chunk in _chunks(content)
        ]
        return sorted(chunks, key=lambda chunk: (_overlap(chunk, terms), len(chunk)), reverse=True)

    @staticmethod
    def _format_turns(turns: list[TerminalHistoryTurn]) -> str:
        return "\n".join(f"{turn.role}: {turn.content}" for turn in turns)


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9_]+", text.lower()) if len(term) > 2}


def _overlap(text: str, terms: set[str]) -> int:
    return len(_terms(text) & terms)


def _chunks(text: str) -> list[str]:
    return [text[index : index + _CHUNK_CHARS] for index in range(0, len(text), _CHUNK_CHARS)] or [""]
