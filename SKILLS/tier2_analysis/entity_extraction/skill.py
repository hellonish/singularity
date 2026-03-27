"""entity_extraction — identifies named entities in upstream text."""
from ..base import BaseAnalysisSkill


class EntityExtractionSkill(BaseAnalysisSkill):
    name = "entity_extraction"
    PROMPT_FILE = "entity_extraction.md"
