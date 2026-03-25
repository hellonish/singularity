"""synthesis — combines findings from multiple upstream sources."""
from .._base import BaseAnalysisSkill


class SynthesisSkill(BaseAnalysisSkill):
    name = "synthesis"
    PROMPT_FILE = "synthesis.md"
