"""gap_analysis — identifies coverage gaps vs. research goal."""
from .._base import BaseAnalysisSkill


class GapAnalysisSkill(BaseAnalysisSkill):
    name = "gap_analysis"
    PROMPT_FILE = "gap_analysis.md"
