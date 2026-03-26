"""timeline_construct — builds chronological event timeline."""
from ..base import BaseAnalysisSkill


class TimelineConstructSkill(BaseAnalysisSkill):
    name = "timeline_construct"
    PROMPT_FILE = "timeline_construct.md"
