from .base import SkillBase
from .registry import SKILL_REGISTRY, TIER1_SKILLS, _register_real_skills
from .skill_docs import SkillDocs

SKILL_DOCS: SkillDocs = SkillDocs()

__all__ = ["SkillBase", "SKILL_REGISTRY", "TIER1_SKILLS", "_register_real_skills", "SKILL_DOCS"]
