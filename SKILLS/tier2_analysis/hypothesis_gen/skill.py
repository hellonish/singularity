"""hypothesis_gen — generates testable hypotheses from evidence gaps."""
from ..base import BaseAnalysisSkill


class HypothesisGenSkill(BaseAnalysisSkill):
    name = "hypothesis_gen"
    PROMPT_FILE = "hypothesis_gen.md"
