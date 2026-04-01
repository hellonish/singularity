"""
Model registry for the Chat Agent.

Lists all available models with their provider, display name, and capability tags.
The /model command in the CLI and ChatAgent both use this registry.
"""
from __future__ import annotations
from dataclasses import dataclass
from llm.router import get_llm_client
from llm.base import BaseLLMClient


@dataclass
class ModelInfo:
    model_id: str
    display_name: str
    provider: str       # "grok" | "gemini" | "deepseek"
    tags: list[str]     # e.g. ["fast", "reasoning", "flagship"]
    description: str


# ---------------------------------------------------------------------------
# Registered models
# ---------------------------------------------------------------------------

AVAILABLE_MODELS: list[ModelInfo] = [
    # ── Grok ──────────────────────────────────────────────────────────
    ModelInfo(
        model_id="grok-3",
        display_name="Grok 3",
        provider="grok",
        tags=["flagship", "powerful"],
        description="xAI's flagship model — best quality for complex tasks",
    ),
    ModelInfo(
        model_id="grok-3-mini",
        display_name="Grok 3 Mini",
        provider="grok",
        tags=["fast", "efficient"],
        description="xAI's fast, cost-efficient model — great for most queries",
    ),
    ModelInfo(
        model_id="grok-3-mini-fast",
        display_name="Grok 3 Mini Fast",
        provider="grok",
        tags=["fast", "efficient"],
        description="Optimized speed variant of Grok 3 Mini",
    ),

    # ── Gemini ────────────────────────────────────────────────────────
    ModelInfo(
        model_id="gemini-2.5-pro-preview-03-25",
        display_name="Gemini 2.5 Pro",
        provider="gemini",
        tags=["flagship", "thinking", "powerful"],
        description="Google's most capable model with extended thinking",
    ),
    ModelInfo(
        model_id="gemini-2.5-flash-preview-04-17",
        display_name="Gemini 2.5 Flash",
        provider="gemini",
        tags=["fast", "efficient"],
        description="Google's fast, efficient latest model",
    ),
    ModelInfo(
        model_id="gemini-2.0-flash",
        display_name="Gemini 2.0 Flash",
        provider="gemini",
        tags=["fast", "multimodal"],
        description="Google Gemini 2.0 — fast with multimodal capabilities",
    ),
    ModelInfo(
        model_id="gemini-2.0-flash-thinking-exp",
        display_name="Gemini 2.0 Flash Thinking",
        provider="gemini",
        tags=["reasoning", "thinking"],
        description="Gemini 2.0 with explicit reasoning / thinking traces",
    ),

    # ── DeepSeek ──────────────────────────────────────────────────────
    ModelInfo(
        model_id="deepseek-chat",
        display_name="DeepSeek V3",
        provider="deepseek",
        tags=["efficient", "capable"],
        description="DeepSeek's standard conversational model",
    ),
    ModelInfo(
        model_id="deepseek-reasoner",
        display_name="DeepSeek R1 (Reasoner)",
        provider="deepseek",
        tags=["reasoning", "powerful"],
        description="DeepSeek's chain-of-thought reasoning model",
    ),
]

# Quick lookup by model_id
MODEL_MAP: dict[str, ModelInfo] = {m.model_id: m for m in AVAILABLE_MODELS}

# Default model
DEFAULT_MODEL_ID = "grok-3-mini"


def get_model_info(model_id: str) -> ModelInfo | None:
    return MODEL_MAP.get(model_id)


def make_client(model_id: str) -> BaseLLMClient:
    """Instantiate the right LLM client for a model_id."""
    return get_llm_client(model_id)
