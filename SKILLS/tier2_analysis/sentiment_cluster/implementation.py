"""sentiment_cluster — clusters social/forum posts by sentiment."""
from .._base import BaseAnalysisSkill


class SentimentClusterSkill(BaseAnalysisSkill):
    name = "sentiment_cluster"
    PROMPT_FILE = "sentiment_cluster.md"
