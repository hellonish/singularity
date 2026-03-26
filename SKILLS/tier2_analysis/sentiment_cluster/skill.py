"""sentiment_cluster — clusters social/forum posts by sentiment."""
from ..base import BaseAnalysisSkill


class SentimentClusterSkill(BaseAnalysisSkill):
    name = "sentiment_cluster"
    PROMPT_FILE = "sentiment_cluster.md"
