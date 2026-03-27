"""meta_analysis — aggregates effect sizes from clinical studies."""
from ..base import BaseAnalysisSkill


class MetaAnalysisSkill(BaseAnalysisSkill):
    name = "meta_analysis"
    PROMPT_FILE = "meta_analysis.md"
