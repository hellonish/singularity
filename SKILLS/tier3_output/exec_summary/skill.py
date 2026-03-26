"""
exec_summary — tier 3 output skill.
"""
from ..base import BaseOutputSkill


class ExecSummarySkill(BaseOutputSkill):
    name = "exec_summary"
    PROMPT_FILE = "exec_summary.md"
    format_type = "exec_summary"
