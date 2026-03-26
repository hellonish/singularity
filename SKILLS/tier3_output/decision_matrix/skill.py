"""
decision_matrix — tier 3 output skill.
"""
from ..base import BaseOutputSkill


class DecisionMatrixSkill(BaseOutputSkill):
    name = "decision_matrix"
    PROMPT_FILE = "decision_matrix.md"
    format_type = "decision_matrix"
