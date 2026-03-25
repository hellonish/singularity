"""citation_graph — maps citation relationships between sources."""
from .._base import BaseAnalysisSkill


class CitationGraphSkill(BaseAnalysisSkill):
    name = "citation_graph"
    PROMPT_FILE = "citation_graph.md"
