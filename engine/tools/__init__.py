"""
tools/ — Tool abstraction layer (Phase 0A).

Each tool wraps a specific data source.  They are registered as trusted,
predefined operations and can be associated with future skills by string ID
without importing or defining those skills.

Quick reference:
  WebSearchTool         — general web search (DuckDuckGo + Tavily fallback)
  WebFetchTool          — guarded webpage extraction
  ArxivTool             — arXiv preprints and papers
  PubMedTool            — PubMed / NCBI biomedical literature
  SemanticScholarTool   — Semantic Scholar academic graph
  GitHubTool            — GitHub repository search
  SecEdgarTool          — SEC EDGAR financial filings
  CourtListenerTool     — US case law (CourtListener)
  ClinicalTrialsTool    — ClinicalTrials.gov registry
  StandardsFetchTool    — NIST publications + IEEE Xplore
  YouTubeTranscriptTool — YouTube video transcripts
  GoogleBooksTool       — Google Books
  DatasetHubTool        — HuggingFace Hub datasets
  PdfReaderTool         — PDF text + table extraction
  TranslationTool       — LibreTranslate + Google Translate fallback
"""
from .base import ToolBase, ToolResult
from .web_search import WebSearchTool
from .web_fetch import WebFetchTool
from .calculator import CalculatorTool
from .current_time import CurrentTimeTool
from .browser_render import BrowserRenderTool
from .sandbox_tools import CodeExecutionTool, DatasetAnalysisTool, RepositoryInspectionTool
from .production_retrieval import ProductionRetrievalTool
from .arxiv_api import ArxivTool
from .pubmed_api import PubMedTool
from .semantic_scholar import SemanticScholarTool
from .github_api import GitHubTool
from .sec_edgar import SecEdgarTool
from .courtlistener import CourtListenerTool
from .clinicaltrials import ClinicalTrialsTool
from .standards_fetch import StandardsFetchTool
from .youtube_transcript import YouTubeTranscriptTool
from .google_books import GoogleBooksTool
from .dataset_hub import DatasetHubTool
from .pdf_reader import PdfReaderTool
from .translation import TranslationTool
from .registry import TOOL_REGISTRY, ToolDescriptor, ToolRegistry

for _tool_class in (
    WebSearchTool,
    WebFetchTool,
    CalculatorTool,
    CurrentTimeTool,
    BrowserRenderTool,
    RepositoryInspectionTool,
    DatasetAnalysisTool,
    CodeExecutionTool,
    ProductionRetrievalTool,
    ArxivTool,
    PubMedTool,
    SemanticScholarTool,
    GitHubTool,
    SecEdgarTool,
    CourtListenerTool,
    ClinicalTrialsTool,
    StandardsFetchTool,
    YouTubeTranscriptTool,
    GoogleBooksTool,
    DatasetHubTool,
    PdfReaderTool,
    TranslationTool,
):
    TOOL_REGISTRY.register(_tool_class)

__all__ = [
    "ToolBase", "ToolResult",
    "WebSearchTool",
    "WebFetchTool",
    "CalculatorTool",
    "CurrentTimeTool",
    "BrowserRenderTool",
    "RepositoryInspectionTool",
    "DatasetAnalysisTool",
    "CodeExecutionTool",
    "ProductionRetrievalTool",
    "ArxivTool",
    "PubMedTool",
    "SemanticScholarTool",
    "GitHubTool",
    "SecEdgarTool",
    "CourtListenerTool",
    "ClinicalTrialsTool",
    "StandardsFetchTool",
    "YouTubeTranscriptTool",
    "GoogleBooksTool",
    "DatasetHubTool",
    "PdfReaderTool",
    "TranslationTool",
    "TOOL_REGISTRY",
    "ToolDescriptor",
    "ToolRegistry",
]
