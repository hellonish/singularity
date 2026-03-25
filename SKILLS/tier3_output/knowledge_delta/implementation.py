"""
knowledge_delta — tier 3 output skill.
"""
from .._base import BaseOutputSkill


class KnowledgeDeltaSkill(BaseOutputSkill):
    name = "knowledge_delta"
    PROMPT_FILE = "knowledge_delta.md"
    format_type = "knowledge_delta"
