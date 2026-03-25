"""
tools/ — Tool abstraction layer (Phase 0A).

Each tool wraps a specific data source.
Import the class you need, call `tool.call_with_retry(query, **kwargs)`.

Quick reference:
  WebFetchTool          — general web search (DuckDuckGo + Tavily fallback)
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
from .web_fetch import WebFetchTool
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

__all__ = [
    "ToolBase", "ToolResult",
    "WebFetchTool",
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
]
