"""
Centralised configuration — edit here to change models, limits, and paths.
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT  = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "planner" / "domain_registry.json"

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

# Single cheap classifier call for domain routing (Phase A retrieval)
DOMAIN_CLASSIFIER_MODEL      = "grok-3-mini"
MAX_TOKENS_DOMAIN_CLASSIFIER = 96

# Tiered model routing
#
# All roles use fast non-reasoning models only.
# grok-3-mini  — planner, managers, analysis calls   ($0.25/$0.50 per M)
# grok-3       — lead synthesis, section writing      ($3.00/$15.00 per M)

MANAGER_MODEL         = "grok-3-mini"   # 3 structural proposals
LEAD_MODEL            = "grok-3"        # 1 synthesis/merge call
WORKER_ANALYSIS_MODEL = "grok-3-mini"   # Call 1 (analysis) — high-volume structured JSON
WORKER_WRITE_MODEL    = "grok-3"        # Call 2 (section write) — the final product
WORKER_MODEL          = WORKER_WRITE_MODEL
POLISHER_MODEL        = "grok-3-mini"   # Phase D polish — parallel, formatting-focused
SOURCE_GATE_MODEL     = "grok-3-mini"   # 2-pass source gate — per-skill aggregate Grok call

# ---------------------------------------------------------------------------
# Chat Agent
# ---------------------------------------------------------------------------
CHAT_THINKER_MODEL  = "grok-3-mini"   # Thinking layer — skill selection + step plan
CHAT_RESPONSE_MODEL = "grok-3-mini"   # Chat mode generation (upgrade to grok-3 for quality)
