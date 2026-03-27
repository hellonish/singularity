"""
knowledge_delta — tier 3 output skill.
"""
from ..base import BaseOutputSkill


class KnowledgeDeltaSkill(BaseOutputSkill):
    name = "knowledge_delta"
    PROMPT_FILE = "knowledge_delta.md"
    format_type = "knowledge_delta"
