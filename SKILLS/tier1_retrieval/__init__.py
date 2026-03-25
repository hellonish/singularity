"""
Tier-1 retrieval skills — real implementations of all 18 retrieval nodes.

Each skill lives in its own directory:
  skills/tier1_retrieval/<skill_name>/
    skill.md            ← description, when to use, output contract
    implementation.py   ← Python class
    __init__.py

Registered into SKILL_REGISTRY by orchestrator/__init__.py at import time.
"""
from .web_search.implementation        import WebSearchSkill
from .academic_search.implementation  import AcademicSearchSkill
from .clinical_search.implementation  import ClinicalSearchSkill
from .legal_search.implementation     import LegalSearchSkill
from .financial_search.implementation import FinancialSearchSkill
from .news_archive.implementation     import NewsArchiveSkill
from .gov_search.implementation       import GovSearchSkill
from .code_search.implementation      import CodeSearchSkill
from .patent_search.implementation    import PatentSearchSkill
from .standards_search.implementation import StandardsSearchSkill
from .forum_search.implementation     import ForumSearchSkill
from .video_search.implementation     import VideoSearchSkill
from .dataset_search.implementation   import DatasetSearchSkill
from .book_search.implementation      import BookSearchSkill
from .social_search.implementation    import SocialSearchSkill
from .pdf_deep_extract.implementation import PdfDeepExtractSkill
from .multimedia_search.implementation import MultimediaSearchSkill
from .data_extraction.implementation  import DataExtractionSkill

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
