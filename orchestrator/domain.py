"""
DomainRegistry — loads domain_registry.json and exposes lookup helpers.
"""
import json
from pathlib import Path


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
        """Returns (domain_key, confidence) where confidence is 'high' | 'medium' | 'low'."""
        problem_lower = problem.lower()
        scores: dict[str, int] = {
            key: sum(1 for s in domain.get("detection_signals", []) if s.lower() in problem_lower)
            for key, domain in self._data["domains"].items()
            if key != "general"
        }
        scores = {k: v for k, v in scores.items() if v > 0}

        if not scores:
            return "general", "low"

        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Tie → fall back to general
        if len(top) >= 2 and top[0][1] == top[1][1]:
            return "general", "low"

        best_key, best_score = top[0]
        confidence = "high" if best_score >= 3 else "medium" if best_score >= 2 else "low"
        return best_key, confidence
