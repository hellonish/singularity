"""
explainer — tier 3 output skill.
"""
from ..base import BaseOutputSkill


class ExplainerSkill(BaseOutputSkill):
    name = "explainer"
    PROMPT_FILE = "explainer.md"
    format_type = "explainer"
