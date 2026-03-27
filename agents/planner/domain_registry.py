"""
DomainRegistry — loads domain_registry.json and exposes lookup helpers.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _signal_weight(signal: str) -> float:
    """
    Prefer multi-word and hyphenated phrases (more specific) over short tokens
    that appear in many domains (e.g. 'model', 'case', 'report').
    """
    s = signal.strip()
    if " " in s:
        return 4.0
    if "-" in s:
        return 3.0
    if len(s) >= 10:
        return 2.5
    if len(s) >= 6:
        return 2.0
    return 1.0


def _signal_matches(problem_lower: str, signal: str) -> bool:
    """
    Match a detection signal against the problem text.

    Uses word-boundary style checks so short tokens do not match inside
    unrelated words ('law' in 'flaw', 'case' in 'casey', 'war' in 'toward').
    Multi-word signals must appear as contiguous phrases.
    """
    sig = signal.lower().strip()
    if not sig:
        return False
    # Phrase: space-separated words
    if " " in sig:
        return bool(
            re.search(
                r"(?<!\w)" + re.escape(sig) + r"(?!\w)",
                problem_lower,
                flags=re.IGNORECASE,
            )
        )
    # hyphenated token (e.g. fine-tuning, meta-analysis, fact-check)
    if "-" in sig:
        return bool(
            re.search(
                r"(?<!\w)" + re.escape(sig) + r"(?!\w)",
                problem_lower,
                flags=re.IGNORECASE,
            )
        )
    # Single token
    return bool(
        re.search(r"(?<!\w)" + re.escape(sig) + r"(?!\w)", problem_lower, flags=re.IGNORECASE)
    )


class DomainRegistry:
    def __init__(self, path: Path):
        self._data = json.loads(path.read_text(encoding="utf-8"))

    def get_domain(self, key: str) -> dict:
        return self._data["domains"].get(key, self._data["domains"]["general"])

    def get_fallback_chain(self, skill: str) -> list[str]:
        return self._data["fallback_chains"].get(skill, ["web_search"])

    def get_audience_rules(self, audience: str) -> dict:
        return self._data["audience_output_rules"].get(
            audience, self._data["audience_output_rules"]["practitioner"])

    def get_skill_meta(self, skill: str) -> dict:
        for tier in self._data["skill_registry"].values():
            if skill in tier:
                return tier[skill]
        return {"desc": skill, "cost": "unknown", "latency": "unknown"}

    def detect_domain(self, problem: str) -> tuple[str, str]:
        """
        Returns (domain_key, confidence) where confidence is 'high' | 'medium' | 'low'.

        Uses weighted phrase/token matching (not naive substring count):
        - Short tokens like 'law', 'case', 'war' no longer match inside unrelated words.
        - Multi-word signals count more than generic single tokens.
        - Ties are broken by match count, then domain key (deterministic) — never
          forced to 'general' solely because two domains had the same *integer* count.
        """
        problem_lower = problem.lower()

        weighted: dict[str, float] = {}
        match_counts: dict[str, int] = {}

        for key, domain in self._data["domains"].items():
            if key == "general":
                continue
            total = 0.0
            n_hit = 0
            for s in domain.get("detection_signals", []):
                if _signal_matches(problem_lower, s):
                    total += _signal_weight(s)
                    n_hit += 1
            if total > 0:
                weighted[key] = total
                match_counts[key] = n_hit

        if not weighted:
            return "general", "low"

        # Highest weighted score wins; tie-break: more distinct signals, then stable key order
        ranked = sorted(
            weighted.items(),
            key=lambda kv: (-kv[1], -match_counts[kv[0]], kv[0]),
        )
        best_key, best_w = ranked[0]

        # Confidence from weighted mass (not raw hit count)
        if best_w >= 8.0 or match_counts[best_key] >= 4:
            confidence = "high"
        elif best_w >= 4.0 or match_counts[best_key] >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        return best_key, confidence

    def detect_domain_llm(
        self,
        problem: str,
        client: Any,
        *,
        max_tokens: int = 96,
    ) -> tuple[str, str]:
        """
        Classify the research question with one small LLM call (cheap: short
        system prompt, capped completion tokens). Returns (domain_key, confidence).

        Falls back to :meth:`detect_domain` heuristics if the model output is not
        valid JSON or the domain key is unknown.
        """
        keys_lines = "\n".join(
            f"  {k} — {self._data['domains'][k].get('label', k)}"
            for k in self._data["domains"].keys()
        )
        system = (
            "You classify a research question into exactly ONE domain key for "
            "routing retrieval and planning.\n"
            'Respond with ONLY valid JSON: '
            '{"domain":"<key>","confidence":"high"|"medium"|"low"}\n'
            "No markdown fences, no other text.\n\n"
            f"Allowed keys:\n{keys_lines}\n\n"
            'Prefer the most specific domain. Use "general" only when none fit.'
        )
        user = f"Research question:\n{problem.strip()[:6000]}"
        try:
            raw = client.generate_text(
                prompt=user,
                system_prompt=system,
                temperature=0.1,
                max_tokens=max_tokens,
            )
        except Exception:
            return self.detect_domain(problem)

        parsed = _parse_domain_classifier_json(raw)
        if not isinstance(parsed, dict):
            return self.detect_domain(problem)

        key = str(parsed.get("domain", "")).strip()
        conf = str(parsed.get("confidence", "medium")).strip().lower()
        if key not in self._data["domains"]:
            return self.detect_domain(problem)
        if conf not in ("high", "medium", "low"):
            conf = "medium"
        return key, conf


def _parse_domain_classifier_json(raw: str) -> dict | None:
    """Extract {\"domain\":...,\"confidence\":...} from model output."""
    raw = raw.strip()
    for block in re.findall(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL):
        try:
            obj = json.loads(block.strip())
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[^{}]*\"domain\"[^{}]*\}", raw, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None
