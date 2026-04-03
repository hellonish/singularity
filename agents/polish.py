"""Phase D — Report Polish

Two-stage polish of the assembled markdown report.

Stage 1 — Programmatic (zero cost, deterministic):
  • backslash-paren math  -> dollar-sign math  (inline)
  • backslash-bracket math -> double-dollar math (display)

Stage 2 — LLM creative (section-by-section, parallel):
  • Convert prose comparisons to tables
  • Add callout blockquotes for key findings / definitions
  • Expand malformed single-line tables to multi-line GFM
  • Add visual separators between logical blocks
  • Preserve all facts, citations, and math content verbatim
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm.base import BaseLLMClient
    from trace import TraceLogger

_PROMPT_PATH = Path(__file__).parent / "report_polisher" / "system_prompt.md"


# ---------------------------------------------------------------------------
# Stage 1: Programmatic fixes
# ---------------------------------------------------------------------------

def _programmatic_fixes(md: str) -> str:
    """Deterministic rendering-correctness fixes — no LLM, instant."""
    # \(...\) → $...$
    md = re.sub(r'\\\((.+?)\\\)', lambda m: f'${m.group(1)}$', md, flags=re.DOTALL)
    # \[...\] → $$\n...\n$$
    md = re.sub(r'\\\[(.+?)\\\]', lambda m: f'$$\n{m.group(1).strip()}\n$$', md, flags=re.DOTALL)
    return md


# ---------------------------------------------------------------------------
# Stage 2: LLM polish
# ---------------------------------------------------------------------------

def _split_sections(md: str) -> list[str]:
    """
    Split the report into chunks at every top-level ## heading.
    The preamble (everything before the first ##) becomes chunk 0.
    Each ## section (including its ### children) is one chunk.
    """
    parts = re.split(r'(?=^## )', md, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def _reassemble(sections: list[str]) -> str:
    return "\n\n".join(sections)


async def _polish_section(
    client,
    system_prompt: str,
    section: str,
    query: str,
    audience: str,
    idx: int,
    total: int,
    logger: "TraceLogger | None" = None,
) -> str:
    """Send one section to the LLM polisher and return polished markdown."""
    prompt = (
        f"research_query: {query}\n"
        f"audience: {audience}\n"
        f"section: {idx + 1} of {total}\n\n"
        f"---BEGIN SECTION---\n{section}\n---END SECTION---"
    )
    result = await asyncio.to_thread(
        client.generate_text,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.35,
    )
    # Strip any accidental code-fence wrapper the LLM may have added
    result = result.strip()
    result = re.sub(r'^```(?:markdown)?\n?', '', result)
    result = re.sub(r'\n?```$', '', result)
    polished = result.strip() or section   # fall back to original if LLM returns empty

    if logger is not None:
        logger.log_polish(
            system_prompt=system_prompt,
            user_message=prompt,
            raw_response=result,
            section_idx=idx,
        )

    return polished


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class PolishAgent:
    """
    Phase D polish using an injected LLM client (same BYOK model as the rest of the pipeline).
    """

    def __init__(
        self,
        client: "BaseLLMClient",
        logger: "TraceLogger | None" = None,
    ) -> None:
        self.client = client
        self._system_prompt: str = _PROMPT_PATH.read_text(encoding="utf-8")
        self._logger = logger

    async def polish(self, report_md: str, query: str, audience: str) -> str:
        """
        Full two-stage polish.

        1. Programmatic fixes (always applied — free).
        2. LLM section polish in parallel — all ## sections run concurrently.

        Returns polished markdown string.
        """
        # Stage 1
        md = _programmatic_fixes(report_md)

        # Stage 2
        sections = _split_sections(md)

        tasks = [
            _polish_section(
                self.client, self._system_prompt,
                sec, query, audience, i, len(sections),
                logger=self._logger,
            )
            for i, sec in enumerate(sections)
        ]
        polished = await asyncio.gather(*tasks)

        return _reassemble(list(polished))
