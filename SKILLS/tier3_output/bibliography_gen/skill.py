"""
bibliography_gen — tier 3 output skill.
"""
from ..base import BaseOutputSkill


class BibliographyGenSkill(BaseOutputSkill):
    name = "bibliography_gen"
    PROMPT_FILE = "bibliography_gen.md"
    format_type = "bibliography"
