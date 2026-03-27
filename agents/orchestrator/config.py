"""
Centralised configuration — edit here to change models, limits, and paths.
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT   = Path(__file__).resolve().parent.parent.parent
SKILL_PATH     = Path(__file__).resolve().parent.parent / "planner" / "system_prompt.md"
REGISTRY_PATH  = Path(__file__).resolve().parent.parent / "planner" / "domain_registry.json"
PLANNER_OUTPUT = PROJECT_ROOT / "planner_output.md"

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
PLANNER_MODEL      = "grok-3-mini"
MAX_TOKENS_PLANNER = 6000

# Phase 5 — tiered model routing
#
# Cost/quality assignment (Strength 4, ~32 sections):
#   PLANNER + MANAGERS + WORKER_ANALYSIS  → grok-3-mini   ($0.25/$0.50 per M)
#   LEAD                                  → grok-4 reason  ($2.00/$6.00 per M) — 1 call
#   WORKER_WRITE                          → grok-4         ($2.00/$6.00 per M) — 32 calls
#
#   Total estimated cost at Strength 4: ≈ $0.64 vs $0.12 all-mini
#   The Lead reasoning call is a 1× cost; Writer quality affects every section.

MANAGER_MODEL         = "grok-3-mini"          # 3 structural proposals — mini sufficient
LEAD_MODEL            = "grok-4-0709"          # 1 reasoning synthesis call — upgrade justified
WORKER_ANALYSIS_MODEL = "grok-3-mini"          # Call 1 (analysis) — high-volume, structured JSON
WORKER_WRITE_MODEL    = "grok-4-0709"          # Call 2 (section write) — this IS the product

# Legacy alias kept for any code outside Phase C that still imports WORKER_MODEL
WORKER_MODEL = WORKER_WRITE_MODEL

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
