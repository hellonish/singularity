"""statistical_analysis — extracts and computes descriptive statistics."""
from .._base import BaseAnalysisSkill


class StatisticalAnalysisSkill(BaseAnalysisSkill):
    name = "statistical_analysis"
    PROMPT_FILE = "statistical_analysis.md"
