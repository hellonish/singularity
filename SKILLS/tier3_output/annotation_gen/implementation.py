"""
annotation_gen — tier 3 output skill.
"""
from .._base import BaseOutputSkill


class AnnotationGenSkill(BaseOutputSkill):
    name = "annotation_gen"
    PROMPT_FILE = "annotation_gen.md"
    format_type = "annotation"
