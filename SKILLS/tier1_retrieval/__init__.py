"""
Tier-1 retrieval skills — real implementations of all 18 retrieval nodes.

Each skill lives in its own directory:
  skills/tier1_retrieval/<skill_name>/
    skill.md            ← description, when to use, output contract
    skill.py            ← Python class
    __init__.py

Registered into SKILL_REGISTRY by agents/orchestrator/__init__.py at import time.
"""
from .web_search.skill        import WebSearchSkill
from .academic_search.skill  import AcademicSearchSkill
from .clinical_search.skill  import ClinicalSearchSkill
from .legal_search.skill     import LegalSearchSkill
from .financial_search.skill import FinancialSearchSkill
from .news_archive.skill     import NewsArchiveSkill
from .gov_search.skill       import GovSearchSkill
from .code_search.skill      import CodeSearchSkill
from .patent_search.skill    import PatentSearchSkill
from .standards_search.skill import StandardsSearchSkill
from .forum_search.skill     import ForumSearchSkill
from .video_search.skill     import VideoSearchSkill
from .dataset_search.skill   import DatasetSearchSkill
from .book_search.skill      import BookSearchSkill
from .social_search.skill    import SocialSearchSkill
from .pdf_deep_extract.skill import PdfDeepExtractSkill
from .multimedia_search.skill import MultimediaSearchSkill
from .data_extraction.skill  import DataExtractionSkill

__all__ = [
    "WebSearchSkill",
    "AcademicSearchSkill",
    "ClinicalSearchSkill",
    "LegalSearchSkill",
    "FinancialSearchSkill",
    "NewsArchiveSkill",
    "GovSearchSkill",
    "CodeSearchSkill",
    "PatentSearchSkill",
    "StandardsSearchSkill",
    "ForumSearchSkill",
    "VideoSearchSkill",
    "DatasetSearchSkill",
    "BookSearchSkill",
    "SocialSearchSkill",
    "PdfDeepExtractSkill",
    "MultimediaSearchSkill",
    "DataExtractionSkill",
]
