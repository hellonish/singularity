"""
Centralised configuration — edit here to change models, limits, and paths.
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT   = Path(__file__).resolve().parent.parent
SKILL_PATH     = PROJECT_ROOT / "SKILLS" / "PLANNER.md"
REGISTRY_PATH  = PROJECT_ROOT / "planner" / "domain_registry.json"
PLANNER_OUTPUT = PROJECT_ROOT / "orchestrator" / "planner_output.md"

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
PLANNER_MODEL      = "grok-3-mini-fast"
MAX_TOKENS_PLANNER = 6000

# ---------------------------------------------------------------------------
# Execution limits
# ---------------------------------------------------------------------------
MAX_REPLAN_ROUNDS = 4
MAX_NODES         = 15
RETRY_BACKOFF     = [1, 4]   # seconds between retries (len + 1 = total attempts)

# ---------------------------------------------------------------------------
# Credibility adjustments per fallback level
# ---------------------------------------------------------------------------
CREDIBILITY_ADJ: dict[str, float] = {
    "primary":       0.0,
    "fallback_1":   -0.05,
    "fallback_2":   -0.15,
    "web_search":   -0.10,
    "forum_search": -0.20,
    "social_search":-0.25,
}
