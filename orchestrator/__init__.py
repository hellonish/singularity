from .runner import run_orchestrator
from .skills import SKILL_REGISTRY


def _register_real_skills() -> None:
    """
    Swap stub implementations for real tier-1, tier-2, and tier-3 skills.
    Done lazily here (not at module level) to avoid circular imports.
    Falls back to stubs silently if the skills package is unavailable.
    """
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
        return   # skills package not yet available — keep stubs

    SKILL_REGISTRY.update({
        # Tier 1
        "web_search":        WebSearchSkill(),
        "academic_search":   AcademicSearchSkill(),
        "clinical_search":   ClinicalSearchSkill(),
        "legal_search":      LegalSearchSkill(),
        "financial_search":  FinancialSearchSkill(),
        "news_archive":      NewsArchiveSkill(),
        "gov_search":        GovSearchSkill(),
        "code_search":       CodeSearchSkill(),
        "patent_search":     PatentSearchSkill(),
        "standards_search":  StandardsSearchSkill(),
        "forum_search":      ForumSearchSkill(),
        "video_search":      VideoSearchSkill(),
        "dataset_search":    DatasetSearchSkill(),
        "book_search":       BookSearchSkill(),
        "social_search":     SocialSearchSkill(),
        "pdf_deep_extract":  PdfDeepExtractSkill(),
        "multimedia_search": MultimediaSearchSkill(),
        "data_extraction":   DataExtractionSkill(),
        # Tier 2
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
        # Tier 3
        "report_generator":   ReportGeneratorSkill(),
        "exec_summary":       ExecSummarySkill(),
        "bibliography_gen":   BibliographyGenSkill(),
        "decision_matrix":    DecisionMatrixSkill(),
        "explainer":          ExplainerSkill(),
        "annotation_gen":     AnnotationGenSkill(),
        "visualization_spec": VisualizationSpecSkill(),
        "knowledge_delta":    KnowledgeDeltaSkill(),
    })


_register_real_skills()

__all__ = ["run_orchestrator"]
