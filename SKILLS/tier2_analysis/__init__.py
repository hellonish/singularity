"""Tier-2 analysis skills.

Importing this package automatically imports every ``<skill>/skill.py`` module
found in the skill subdirectories.  Each import triggers
``SkillBase.__init_subclass__``, which self-registers the skill class into
``skills.base._SKILL_REGISTRY``.

To add a new tier-2 skill: create the directory and ``skill.py`` — no changes
here are required.
"""
import importlib
from pathlib import Path

_HERE = Path(__file__).parent
for _skill_dir in sorted(_HERE.iterdir()):
    if _skill_dir.is_dir() and not _skill_dir.name.startswith("_"):
        importlib.import_module(f"{__name__}.{_skill_dir.name}")
