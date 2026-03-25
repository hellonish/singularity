"""
visualization_spec — tier 3 output skill.
"""
from .._base import BaseOutputSkill


class VisualizationSpecSkill(BaseOutputSkill):
    name = "visualization_spec"
    PROMPT_FILE = "visualization_spec.md"
    format_type = "visualization_spec"
