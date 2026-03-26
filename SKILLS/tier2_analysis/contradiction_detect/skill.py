"""contradiction_detect — flags contradicting claims across sources."""
from ..base import BaseAnalysisSkill


class ContradictionDetectSkill(BaseAnalysisSkill):
    name = "contradiction_detect"
    PROMPT_FILE = "contradiction_detect.md"
