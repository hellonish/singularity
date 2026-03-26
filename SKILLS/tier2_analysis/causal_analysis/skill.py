"""causal_analysis — distinguishes correlation from causation."""
from ..base import BaseAnalysisSkill


class CausalAnalysisSkill(BaseAnalysisSkill):
    name = "causal_analysis"
    PROMPT_FILE = "causal_analysis.md"
