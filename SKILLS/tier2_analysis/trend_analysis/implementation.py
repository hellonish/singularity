"""trend_analysis — identifies directional trends across dated sources."""
from .._base import BaseAnalysisSkill


class TrendAnalysisSkill(BaseAnalysisSkill):
    name = "trend_analysis"
    PROMPT_FILE = "trend_analysis.md"
