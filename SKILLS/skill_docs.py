"""
SkillDocs — parses every skill's skill.md file at startup.

Two consumers:
  - Thinker (skill selection): needs a compact USE/NOT hint per skill so the
    LLM can choose correctly without blowing up context.
  - Report-pipeline planner (DAG construction): needs the full "When to Use" +
    "Output Contract" for the skills it is about to assign to nodes.

Parsing contract
----------------
All 44 skill.md files share the same section structure:
  ## Description       (verbose — not used here)
  ## When to Use       (USE / NOT signals extracted for thinker menu)
  ## Output Contract   (compact one-liner — used in planner context)
  ## Constraints       (included verbatim in planner context)

Both outputs are built once at import and cached.
"""
from __future__ import annotations

import re
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent
_TIER_DIRS = ["tier1_retrieval", "tier2_analysis", "tier3_output"]
_TIER_LABELS = {
    "tier1_retrieval": "Tier 1 — Retrieval",
    "tier2_analysis":  "Tier 2 — Analysis",
    "tier3_output":    "Tier 3 — Output",
}

# Section-header line: isolated bold label (before or after stripping bullets)
# Covers both "**Label**:" and "**Label:**" formats
_SUBHEADING_LINE = re.compile(r"^\*\*[^*]+\*\*:?\s*$|^\*\*[^*]+:\*\*\s*$")
# "When NOT to Use" or "Edge Cases" section headers that flip the mode
_NOT_SECTION_HDR = re.compile(
    r"\*\*(when\s+not|edge\s+cases|not\s+to\s+use|do\s+not\s+use"
    r"|when\s+to\s+avoid)\b", re.IGNORECASE
)
# Strong negative guidance phrases — NOT bare "not" (to avoid false positives)
_NOT_KW = re.compile(
    r"\b(do\s+not\s+use|do\s+not\s+apply|never\s+use|never\s+apply|"
    r"avoid\s+using|avoid\s+this|should\s+not\s+be\s+used|"
    r"NOT\s+to\s+be\s+used|not\s+intended)\b",
    re.IGNORECASE,
)
# Structural metadata lines — upstream/downstream wiring, not use-case signal
_META_LINE = re.compile(
    r"\b(upstream|downstream|dependency|dependencies|following this|prior to|"
    r"input\s+should|expects?\s+(a|an|the)|requires?\s+(an?\s+)?upstream)\b",
    re.IGNORECASE,
)
# Generic list-intro phrases with no signal (followed by bullet lists, not content)
_GENERIC_INTRO = re.compile(
    r"^use\s+this\s+skill\s+in\s+the\s+following|"
    r"^this\s+skill\s+(should\s+be\s+(used|deployed)|is\s+(used|a))\s+in\s+(any|all|the\s+following)",
    re.IGNORECASE,
)


def _read_section(text: str, header: str) -> str:
    """Return the body of a ## Section, stripped. Empty string if absent."""
    m = re.search(
        rf"##\s+{re.escape(header)}\s*\n(.*?)(?=\n##\s|\Z)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    return m.group(1).strip() if m else ""


def _extract_use_not(when_text: str) -> tuple[str, str]:
    """
    Distil a "When to Use" section body into a (use_hint, not_hint) pair,
    each a short string for the thinker menu's USE / NOT columns.

    Strategy
    --------
    1. Walk lines, stripping bullet markers and bold formatting.
    2. Skip section subheadings (isolated bold labels like **Specific Scenarios**).
    3. Skip structural metadata (upstream/downstream wiring text).
    4. When a "When NOT to Use" subheading is encountered, flip into NOT mode.
    5. Classify remaining lines as USE or NOT via _NOT_KW keyword check.
    6. Return first substantive line from each class, truncated to 120 chars.
    """
    use_frags: list[str] = []
    not_frags: list[str] = []
    in_not_section = False

    for raw_line in when_text.split("\n"):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Strip bullet/numbering prefix
        cleaned = re.sub(r"^[\-\*\d\.]+\s*", "", stripped).strip()

        # Check for a NOT-section subheading before stripping bold
        if _NOT_SECTION_HDR.search(cleaned):
            in_not_section = True
            continue

        # Strip bold markers → plain text
        plain = re.sub(r"\*\*([^*]+)\*\*:?", r"\1", cleaned).strip()

        # Skip isolated subheading lines (bold-only) and very short lines.
        # Check both `stripped` (catches bold-only lines without a bullet prefix)
        # and `cleaned` (catches bold-only lines that had a bullet stripped).
        if _SUBHEADING_LINE.match(stripped) or _SUBHEADING_LINE.match(cleaned) or len(plain) < 20:
            in_not_section = False  # reset on any non-NOT subheading
            continue

        # Skip structural metadata (upstream/downstream wiring)
        if _META_LINE.search(plain):
            continue

        # Skip generic intro sentences that carry no specific signal
        if _GENERIC_INTRO.match(plain):
            continue

        if in_not_section or _NOT_KW.search(plain):
            not_frags.append(plain[:120])
        else:
            use_frags.append(plain[:120])

    use_hint = use_frags[0] if use_frags else ""
    not_hint = not_frags[0] if not_frags else ""
    return use_hint, not_hint


class SkillDocs:
    """
    Reads and indexes all 44 skill.md files once at import time.

    thinker_menu()
        Returns a compact text block (~4 k tokens) that replaces the hardcoded
        _SKILL_MENU dict in thinker.py.  One line per skill: name, USE hint,
        NOT hint.  Injected into the thinker system prompt so the LLM can make
        accurate skill-selection decisions.

    planner_context(skill_names)
        Returns the full "When to Use" + "Output Contract" + "Constraints"
        sections for the requested skills only (~500 tokens per skill).
        Passed to the report-pipeline managers and lead so they understand
        what each retrieval skill produces and how to assign it to sections.
    """

    def __init__(self) -> None:
        # name → {"when_to_use": str, "output_contract": str, "constraints": str,
        #          "tier": str, "use_hint": str, "not_hint": str}
        self._index: dict[str, dict[str, str]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def thinker_menu(self) -> str:
        """
        Compact skill list for the thinker system prompt.
        Grouped by tier; one line per skill with USE and NOT hints extracted
        from skill.md.  Replaces the hardcoded _SKILL_MENU dict.
        """
        blocks: list[str] = []
        for tier_dir, tier_label in _TIER_LABELS.items():
            tier_skills = [
                (name, doc)
                for name, doc in self._index.items()
                if doc["tier"] == tier_dir
            ]
            if not tier_skills:
                continue
            blocks.append(tier_label)
            for name, doc in tier_skills:
                use = doc["use_hint"]
                not_ = doc["not_hint"]
                line = f"  {name:<26} USE: {use}"
                if not_:
                    line += f"  |  NOT: {not_}"
                blocks.append(line)
        return "\n".join(blocks)

    def planner_context(self, skill_names: list[str]) -> str:
        """
        Full "When to Use" + "Output Contract" + "Constraints" for the
        requested skills.  Passed to the report-pipeline managers so they
        understand what each skill produces and can wire sections correctly.

        Args:
            skill_names: List of skill name strings (e.g. ["web_search", "synthesis"]).

        Returns:
            Multi-skill markdown block; empty string if none found.
        """
        parts: list[str] = []
        for name in skill_names:
            doc = self._index.get(name)
            if not doc:
                continue
            block = [f"### {name}"]
            if doc["output_contract"]:
                block.append(f"**Output Contract**: {doc['output_contract']}")
            if doc["when_to_use"]:
                block.append(f"**When to Use**:\n{doc['when_to_use']}")
            if doc["constraints"]:
                block.append(f"**Constraints**:\n{doc['constraints']}")
            parts.append("\n".join(block))
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Scan all three tier directories and index every skill.md found."""
        for tier_dir in _TIER_DIRS:
            tier_path = _SKILLS_ROOT / tier_dir
            if not tier_path.is_dir():
                continue
            for skill_dir in sorted(tier_path.iterdir()):
                if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                    continue
                md_path = skill_dir / "skill.md"
                if not md_path.exists():
                    continue
                self._index_skill(md_path, tier_dir)

    def _index_skill(self, md_path: Path, tier_dir: str) -> None:
        """Parse a single skill.md and store its index entry."""
        text = md_path.read_text(encoding="utf-8")
        name = md_path.parent.name

        when_to_use    = _read_section(text, "When to Use")
        output_contract = _read_section(text, "Output Contract")
        constraints    = _read_section(text, "Constraints")

        use_hint, not_hint = _extract_use_not(when_to_use)

        self._index[name] = {
            "tier":            tier_dir,
            "when_to_use":     when_to_use,
            "output_contract": output_contract,
            "constraints":     constraints,
            "use_hint":        use_hint,
            "not_hint":        not_hint,
        }
