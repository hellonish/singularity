"""
ContextBudgetManager — controls how much upstream data is passed to LLM-based
analysis and output skills.

Strategy:
  - Direct dependencies (node.depends_on): full content up to MAX_DIRECT tokens each.
  - Indirect (all other resolved slots): summary only (MAX_INDIRECT chars).
  - Hard cap: truncate least-credible indirect slots if total exceeds MAX_TOTAL.
  - synthesis_hint from the node is always included.
"""
import json
import textwrap
from typing import Any


class ContextBudgetManager:
    MAX_DIRECT_TOKENS: int   = 3000   # ~12 000 chars
    MAX_INDIRECT_CHARS: int  = 350
    MAX_TOTAL_CHARS: int     = 32000  # ~8000 tokens

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def build_context(self, node, ctx) -> str:
        """
        Build a single upstream-context string for an LLM analysis / output
        skill.  `node` is a PlanNode, `ctx` is ExecutionContext.
        """
        direct_ids = set(node.depends_on)
        sections: list[tuple[str, str, float]] = []  # (slot, text, cred)

        for slot, result in ctx.results.items():
            cred = ctx.credibility_scores.get(slot, 0.5)
            raw  = result if isinstance(result, str) else json.dumps(result, default=str)

            # Identify which node_id owns this slot
            is_direct = self._is_direct_dep(slot, direct_ids, ctx)

            if is_direct:
                text = self._truncate(raw, self.MAX_DIRECT_TOKENS * 4)
                sections.append((slot, text, cred))
            else:
                # Summary only — extract "summary" key or shorten
                summary = self._extract_summary(result, raw)
                sections.append((slot, summary, cred))

        # Sort: direct first, then by credibility descending
        sections.sort(key=lambda s: (not self._is_direct_dep(s[0], direct_ids, ctx), -s[2]))

        # Assemble
        parts: list[str] = []

        # Always include synthesis hint
        if node.synthesis_hint:
            parts.append(f"## Synthesis Hint\n{node.synthesis_hint}\n")

        total = sum(len(p) for p in parts)
        for slot, text, cred in sections:
            entry = f"## Upstream: {slot} (credibility={cred:.2f})\n{text}\n"
            if total + len(entry) > self.MAX_TOTAL_CHARS:
                remaining = self.MAX_TOTAL_CHARS - total
                if remaining > 100:
                    parts.append(entry[:remaining] + "\n[...truncated]")
                break
            parts.append(entry)
            total += len(entry)

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _is_direct_dep(slot: str, direct_ids: set[str], ctx) -> bool:
        """Check if slot belongs to a node whose node_id is in direct_ids."""
        # node_status maps node_id → status; results maps output_slot → data
        # We need the reverse: slot → node_id.  Convention: slot often equals
        # node_id or is derivable.  Safest: check if slot name overlaps.
        for nid in direct_ids:
            if nid in slot or slot in nid:
                return True
        return False

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n[...truncated]"

    @staticmethod
    def _extract_summary(result: Any, raw: str) -> str:
        """Pull a short summary from the result dict, or shorten the raw text."""
        if isinstance(result, dict):
            for key in ("summary", "synthesis", "report", "explainer"):
                if key in result and isinstance(result[key], str):
                    return textwrap.shorten(result[key], width=350)
        return textwrap.shorten(raw, width=350)
