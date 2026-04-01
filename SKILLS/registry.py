"""Skill registry — auto-populated via SkillBase.__init_subclass__ on import.

Usage
-----
Call ``_register_real_skills()`` once at startup (done by
``agents/orchestrator/__init__.py``).  After that, import
``SKILL_REGISTRY`` and ``TIER1_SKILLS`` from here.

How registration works
----------------------
1. ``_register_real_skills`` imports all three tier packages.
2. Each tier ``__init__.py`` imports its skill classes.
3. Each class definition triggers ``SkillBase.__init_subclass__``, which
   inserts the class into ``skills.base._SKILL_REGISTRY``.
4. This function then instantiates every registered class into
   ``SKILL_REGISTRY`` and derives ``TIER1_SKILLS`` from those that are
   ``BaseRetrievalSkill`` subclasses.
"""
import logging

from skills.base import SkillBase, _SKILL_REGISTRY

logger = logging.getLogger(__name__)

SKILL_REGISTRY: dict[str, SkillBase] = {}
# Mutable set so that callers using `from skills import TIER1_SKILLS` see
# the populated version after _register_real_skills() runs in-place.
TIER1_SKILLS: set[str] = set()


def _register_real_skills() -> None:
    """Import all skill packages and instantiate every discovered skill class.

    Imports trigger ``SkillBase.__init_subclass__`` on every concrete skill,
    populating ``_SKILL_REGISTRY``.  This function then instantiates each class
    once and derives ``TIER1_SKILLS`` from ``BaseRetrievalSkill`` subclasses.

    Both ``SKILL_REGISTRY`` and ``TIER1_SKILLS`` are mutated in-place so that
    callers who bound them with ``from skills import X`` see the updated values.
    """
    try:
        import skills.tier1_retrieval  # noqa: F401 — side-effect: registers all tier-1 classes
        import skills.tier2_analysis   # noqa: F401 — side-effect: registers all tier-2 classes
        import skills.tier3_output     # noqa: F401 — side-effect: registers all tier-3 classes
    except ImportError as exc:
        logger.error(
            "Skill packages could not be imported — SKILL_REGISTRY will be empty. "
            "Ensure all dependencies are installed. Error: %s",
            exc,
        )
        return

    for name, cls in _SKILL_REGISTRY.items():
        SKILL_REGISTRY[name] = cls()

    # Derive TIER1_SKILLS from the concrete type rather than a hardcoded list.
    from skills.tier1_retrieval.base import BaseRetrievalSkill
    TIER1_SKILLS.update(
        name for name, skill in SKILL_REGISTRY.items()
        if isinstance(skill, BaseRetrievalSkill)
    )

    logger.debug(
        "Skill registry loaded: %d skills (%d tier-1).",
        len(SKILL_REGISTRY),
        len(TIER1_SKILLS),
    )
