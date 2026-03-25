"""
skills/base.py — canonical export point for SkillBase.

Import SkillBase from here (not directly from orchestrator.skills) so the
skills package is the single source of truth.
"""
from orchestrator.skills import SkillBase

__all__ = ["SkillBase"]
