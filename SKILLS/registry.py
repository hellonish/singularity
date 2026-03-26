"""
Skill registry — populated at startup by _register_real_skills().
Import SKILL_REGISTRY and TIER1_SKILLS from here.
"""
from skills.base import SkillBase

TIER1_SKILLS: frozenset[str] = frozenset({
    "web_search", "academic_search", "clinical_search", "legal_search",
    "financial_search", "patent_search", "news_archive", "standards_search",
    "forum_search", "video_search", "dataset_search", "gov_search",
    "book_search", "social_search", "pdf_deep_extract", "multimedia_search",
    "code_search", "data_extraction",
})

SKILL_REGISTRY: dict[str, SkillBase] = {}


def _register_real_skills() -> None:
    """Populate SKILL_REGISTRY with real skill instances."""
    try:
        from skills.tier1_retrieval import (
            WebSearchSkill, AcademicSearchSkill, ClinicalSearchSkill,
            LegalSearchSkill, FinancialSearchSkill, NewsArchiveSkill,
            GovSearchSkill, CodeSearchSkill, PatentSearchSkill,
            StandardsSearchSkill, ForumSearchSkill, VideoSearchSkill,
            DatasetSearchSkill, BookSearchSkill, SocialSearchSkill,
            PdfDeepExtractSkill, MultimediaSearchSkill, DataExtractionSkill,
        )
        from skills.tier2_analysis import (
            SynthesisSkill, ComparativeAnalysisSkill, GapAnalysisSkill,
            QualityCheckSkill, ContradictionDetectSkill, ClaimVerificationSkill,
            CausalAnalysisSkill, StatisticalAnalysisSkill, MetaAnalysisSkill,
            TrendAnalysisSkill, TimelineConstructSkill, HypothesisGenSkill,
            EntityExtractionSkill, CitationGraphSkill, SentimentClusterSkill,
            CredibilityScoreSkill, TranslationSkill, FallbackRouterSkill,
        )
        from skills.tier3_output import (
            ReportGeneratorSkill, ExecSummarySkill, BibliographyGenSkill,
            DecisionMatrixSkill, ExplainerSkill, AnnotationGenSkill,
            VisualizationSpecSkill, KnowledgeDeltaSkill,
        )
    except ImportError:
        return

    SKILL_REGISTRY.update({
        "web_search":         WebSearchSkill(),
        "academic_search":    AcademicSearchSkill(),
        "clinical_search":    ClinicalSearchSkill(),
        "legal_search":       LegalSearchSkill(),
        "financial_search":   FinancialSearchSkill(),
        "news_archive":       NewsArchiveSkill(),
        "gov_search":         GovSearchSkill(),
        "code_search":        CodeSearchSkill(),
        "patent_search":      PatentSearchSkill(),
        "standards_search":   StandardsSearchSkill(),
        "forum_search":       ForumSearchSkill(),
        "video_search":       VideoSearchSkill(),
        "dataset_search":     DatasetSearchSkill(),
        "book_search":        BookSearchSkill(),
        "social_search":      SocialSearchSkill(),
        "pdf_deep_extract":   PdfDeepExtractSkill(),
        "multimedia_search":  MultimediaSearchSkill(),
        "data_extraction":    DataExtractionSkill(),
        "synthesis":            SynthesisSkill(),
        "comparative_analysis": ComparativeAnalysisSkill(),
        "gap_analysis":         GapAnalysisSkill(),
        "quality_check":        QualityCheckSkill(),
        "contradiction_detect": ContradictionDetectSkill(),
        "claim_verification":   ClaimVerificationSkill(),
        "causal_analysis":      CausalAnalysisSkill(),
        "statistical_analysis": StatisticalAnalysisSkill(),
        "meta_analysis":        MetaAnalysisSkill(),
        "trend_analysis":       TrendAnalysisSkill(),
        "timeline_construct":   TimelineConstructSkill(),
        "hypothesis_gen":       HypothesisGenSkill(),
        "entity_extraction":    EntityExtractionSkill(),
        "citation_graph":       CitationGraphSkill(),
        "sentiment_cluster":    SentimentClusterSkill(),
        "credibility_score":    CredibilityScoreSkill(),
        "translation":          TranslationSkill(),
        "fallback_router":      FallbackRouterSkill(),
        "report_generator":   ReportGeneratorSkill(),
        "exec_summary":       ExecSummarySkill(),
        "bibliography_gen":   BibliographyGenSkill(),
        "decision_matrix":    DecisionMatrixSkill(),
        "explainer":          ExplainerSkill(),
        "annotation_gen":     AnnotationGenSkill(),
        "visualization_spec": VisualizationSpecSkill(),
        "knowledge_delta":    KnowledgeDeltaSkill(),
    })
