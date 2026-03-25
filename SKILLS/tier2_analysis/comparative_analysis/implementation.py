"""comparative_analysis — side-by-side evaluation across axes."""
from .._base import BaseAnalysisSkill


class ComparativeAnalysisSkill(BaseAnalysisSkill):
    name = "comparative_analysis"
    PROMPT_FILE = "comparative_analysis.md"
