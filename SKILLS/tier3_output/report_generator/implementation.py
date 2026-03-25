"""
report_generator — tier 3 output skill.
"""
from .._base import BaseOutputSkill


class ReportGeneratorSkill(BaseOutputSkill):
    name = "report_generator"
    PROMPT_FILE = "report_generator.md"
    format_type = "report"
