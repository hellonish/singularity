"""
Chat Agent — dual-mode conversational + research agent.

Usage:
    python -m agents.chat.cli
    python -m agents.chat.cli --extended
"""
from agents.chat.agent import ChatAgent

__all__ = ["ChatAgent"]
