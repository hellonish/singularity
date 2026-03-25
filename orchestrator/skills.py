"""
Skill registry — base class, stub implementations, and the SKILL_REGISTRY dict.

To add a real skill:
  1. Subclass SkillBase (or _SimpleStub for quick prototyping).
  2. Set `name = "your_skill_name"`.
  3. Implement `async run(node, ctx, client, registry) -> (result, NodeStatus, credibility)`.
  4. Add an instance to SKILL_REGISTRY below.
"""
import asyncio
from typing import Any

from .context import ExecutionContext
from .models import NodeStatus, PlanNode


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class SkillBase:
    name: str = "base"

    async def run(
        self,
        node: PlanNode,
        ctx: ExecutionContext,
        client,
        registry,
    ) -> tuple[Any, NodeStatus, float]:
        """Override this. Returns (result, status, credibility 0-1)."""
        raise NotImplementedError


class _SimpleStub(SkillBase):
    """Generic placeholder. Returns a stub result so the DAG can complete end-to-end."""
    async def run(self, node, ctx, client, registry):
        print(f"    [{self.name}] {node.description[:60]}")
        await asyncio.sleep(0.08)
        return {
            "skill": self.name,
            "query": node.description,
            "summary": f"[STUB] {self.name}: {node.description[:80]}",
            "sources": [],
        }, NodeStatus.OK, 0.85


# ---------------------------------------------------------------------------
# Tier 1 — Retrieval  (override run() to make real)
# ---------------------------------------------------------------------------

class WebSearchSkill(_SimpleStub):
    name = "web_search"
    async def run(self, node, ctx, client, registry):
        print(f"    [web_search] {node.description[:60]}")
        await asyncio.sleep(0.1)
        return {
            "sources": [{"url": "https://example.com", "snippet": "stub"}],
            "summary": f"Web search stub: {node.description[:60]}",
        }, NodeStatus.OK, 0.80

class AcademicSearchSkill(_SimpleStub):
    name = "academic_search"
    async def run(self, node, ctx, client, registry):
        print(f"    [academic_search] {node.description[:60]}")
        await asyncio.sleep(0.12)
        return {
            "papers": [{"title": "Paper A", "year": 2024, "url": "https://arxiv.org/stub"}],
            "summary": f"Academic search stub: {node.description[:60]}",
        }, NodeStatus.OK, 0.92

class ClinicalSearchSkill(_SimpleStub):
    name = "clinical_search"
    async def run(self, node, ctx, client, registry):
        print(f"    [clinical_search] {node.description[:60]}")
        await asyncio.sleep(0.12)
        return {
            "trials": [{"nct_id": "NCT00000000", "phase": "III", "status": "Completed"}],
            "summary": f"Clinical search stub: {node.description[:60]}",
        }, NodeStatus.OK, 0.93

class LegalSearchSkill(_SimpleStub):
    name = "legal_search"
    async def run(self, node, ctx, client, registry):
        print(f"    [legal_search] {node.description[:60]}")
        await asyncio.sleep(0.15)
        return {
            "cases": [{"citation": "Stub v. Stub, 2024", "jurisdiction": "EU"}],
            "summary": f"Legal search stub: {node.description[:60]}",
        }, NodeStatus.OK, 0.90

class ForumSearchSkill(_SimpleStub):
    name = "forum_search"
    async def run(self, node, ctx, client, registry):
        await asyncio.sleep(0.08)
        return {
            "posts": [], "summary": f"Forum stub: {node.description[:60]}",
        }, NodeStatus.OK, 0.65

class SocialSearchSkill(_SimpleStub):
    name = "social_search"
    async def run(self, node, ctx, client, registry):
        await asyncio.sleep(0.08)
        return {"posts": [], "sentiment": "mixed"}, NodeStatus.OK, 0.60

# Pure stubs — just set name, override run() when ready
class FinancialSearchSkill(_SimpleStub):  name = "financial_search"
class PatentSearchSkill(_SimpleStub):     name = "patent_search"
class NewsArchiveSkill(_SimpleStub):      name = "news_archive"
class StandardsSearchSkill(_SimpleStub):  name = "standards_search"
class VideoSearchSkill(_SimpleStub):      name = "video_search"
class DatasetSearchSkill(_SimpleStub):    name = "dataset_search"
class GovSearchSkill(_SimpleStub):        name = "gov_search"
class BookSearchSkill(_SimpleStub):       name = "book_search"
class PdfDeepExtractSkill(_SimpleStub):   name = "pdf_deep_extract"
class MultimediaSearchSkill(_SimpleStub): name = "multimedia_search"
class CodeSearchSkill(_SimpleStub):       name = "code_search"
class DataExtractionSkill(_SimpleStub):   name = "data_extraction"


# ---------------------------------------------------------------------------
# Tier 2 — Analysis  (override run() to make real)
# ---------------------------------------------------------------------------

class CredibilityScoreSkill(SkillBase):
    name = "credibility_score"
    async def run(self, node, ctx, client, registry):
        print(f"    [credibility_score] evaluating {node.output_slot}")
        await asyncio.sleep(0.05)
        scores = list(ctx.credibility_scores.values())
        avg = sum(scores) / len(scores) if scores else 0.85
        return {
            "upstream_credibility_avg": avg,
            "conflict_of_interest_flag": avg < 0.75,
            "recommendation": (
                "High confidence — proceed"          if avg >= 0.80 else
                "Moderate confidence — note limits"  if avg >= 0.65 else
                "Low confidence — flag heavily"
            ),
            "scores_by_slot": dict(ctx.credibility_scores),
        }, (NodeStatus.OK if avg >= 0.65 else NodeStatus.PARTIAL), avg

class SynthesisSkill(_SimpleStub):
    name = "synthesis"
    async def run(self, node, ctx, client, registry):
        print(f"    [synthesis] {node.description[:60]}")
        await asyncio.sleep(0.15)
        return {
            "synthesis": f"[STUB] Synthesis: {node.description[:80]}",
            "upstream_inputs": node.depends_on,
            "synthesis_hint_applied": node.synthesis_hint or "none",
        }, NodeStatus.OK, 0.88

class GapAnalysisSkill(_SimpleStub):
    name = "gap_analysis"
    async def run(self, node, ctx, client, registry):
        print(f"    [gap_analysis] {node.description[:60]}")
        await asyncio.sleep(0.08)
        return {
            "gaps": ["Gap 1 stub", "Gap 2 stub"],
            "coverage_assessment": "partial",
        }, NodeStatus.PARTIAL, 0.80

class QualityCheckSkill(_SimpleStub):
    name = "quality_check"
    async def run(self, node, ctx, client, registry):
        await asyncio.sleep(0.05)
        return {
            "axes_checked": node.acceptance,
            "passed": node.acceptance,
            "failed": [],
            "score": 1.0,
        }, NodeStatus.OK, 1.0

class TranslationSkill(_SimpleStub):
    name = "translation"
    async def run(self, node, ctx, client, registry):
        print(f"    [translation] {node.description[:60]}")
        await asyncio.sleep(0.10)
        return {
            "translated": True, "languages_detected": ["auto"], "confidence": 0.90,
        }, NodeStatus.OK, 0.90

# Pure stubs
class ComparativeAnalysisSkill(_SimpleStub):  name = "comparative_analysis"
class EntityExtractionSkill(_SimpleStub):     name = "entity_extraction"
class TimelineConstructSkill(_SimpleStub):    name = "timeline_construct"
class CitationGraphSkill(_SimpleStub):        name = "citation_graph"
class ContradictionDetectSkill(_SimpleStub):  name = "contradiction_detect"
class ClaimVerificationSkill(_SimpleStub):    name = "claim_verification"
class TrendAnalysisSkill(_SimpleStub):        name = "trend_analysis"
class CausalAnalysisSkill(_SimpleStub):       name = "causal_analysis"
class HypothesisGenSkill(_SimpleStub):        name = "hypothesis_gen"
class StatisticalAnalysisSkill(_SimpleStub):  name = "statistical_analysis"
class FallbackRouterSkill(_SimpleStub):       name = "fallback_router"
class MetaAnalysisSkill(_SimpleStub):         name = "meta_analysis"
class SentimentClusterSkill(_SimpleStub):     name = "sentiment_cluster"


# ---------------------------------------------------------------------------
# Tier 3 — Output  (override run() to make real)
# ---------------------------------------------------------------------------

class ReportGeneratorSkill(_SimpleStub):
    name = "report_generator"
    async def run(self, node, ctx, client, registry):
        print(f"    [report_generator] {node.description[:60]}")
        await asyncio.sleep(0.20)
        gaps = [
            slot for slot, status in ctx.node_status.items()
            if status in (NodeStatus.PARTIAL, NodeStatus.FAILED)
        ]
        return {
            "report": f"[STUB] Research report: {node.description[:80]}",
            "coverage_gaps_disclosed": gaps,
            "synthesis_hint": node.synthesis_hint,
            "word_count_estimate": 1200,
        }, NodeStatus.OK, 0.90

class ExecSummarySkill(_SimpleStub):
    name = "exec_summary"
    async def run(self, node, ctx, client, registry):
        print(f"    [exec_summary] {node.description[:60]}")
        await asyncio.sleep(0.10)
        return {
            "summary": f"[STUB] Executive summary: {node.description[:80]}",
            "synthesis_hint": node.synthesis_hint,
            "disclaimer_applied": "disclaimer" in (node.description or "").lower(),
        }, NodeStatus.OK, 0.90

class ExplainerSkill(_SimpleStub):
    name = "explainer"
    async def run(self, node, ctx, client, registry):
        print(f"    [explainer] {node.description[:60]}")
        await asyncio.sleep(0.12)
        return {
            "explainer": f"[STUB] Accessible explainer: {node.description[:80]}",
            "audience_hint": node.synthesis_hint,
        }, NodeStatus.OK, 0.88

# Pure stubs
class BibliographyGenSkill(_SimpleStub):   name = "bibliography_gen"
class DecisionMatrixSkill(_SimpleStub):    name = "decision_matrix"
class AnnotationGenSkill(_SimpleStub):     name = "annotation_gen"
class VisualizationSpecSkill(_SimpleStub): name = "visualization_spec"
class KnowledgeDeltaSkill(_SimpleStub):    name = "knowledge_delta"


# ---------------------------------------------------------------------------
# Registry — add new skill instances here
# ---------------------------------------------------------------------------

SKILL_REGISTRY: dict[str, SkillBase] = {
    # Tier 1 — Retrieval
    "web_search":         WebSearchSkill(),
    "academic_search":    AcademicSearchSkill(),
    "clinical_search":    ClinicalSearchSkill(),
    "legal_search":       LegalSearchSkill(),
    "financial_search":   FinancialSearchSkill(),
    "patent_search":      PatentSearchSkill(),
    "news_archive":       NewsArchiveSkill(),
    "standards_search":   StandardsSearchSkill(),
    "forum_search":       ForumSearchSkill(),
    "video_search":       VideoSearchSkill(),
    "dataset_search":     DatasetSearchSkill(),
    "gov_search":         GovSearchSkill(),
    "book_search":        BookSearchSkill(),
    "social_search":      SocialSearchSkill(),
    "pdf_deep_extract":   PdfDeepExtractSkill(),
    "multimedia_search":  MultimediaSearchSkill(),
    "code_search":        CodeSearchSkill(),
    "data_extraction":    DataExtractionSkill(),
    # Tier 2 — Analysis
    "synthesis":             SynthesisSkill(),
    "comparative_analysis":  ComparativeAnalysisSkill(),
    "gap_analysis":          GapAnalysisSkill(),
    "quality_check":         QualityCheckSkill(),
    "translation":           TranslationSkill(),
    "entity_extraction":     EntityExtractionSkill(),
    "timeline_construct":    TimelineConstructSkill(),
    "citation_graph":        CitationGraphSkill(),
    "contradiction_detect":  ContradictionDetectSkill(),
    "claim_verification":    ClaimVerificationSkill(),
    "trend_analysis":        TrendAnalysisSkill(),
    "causal_analysis":       CausalAnalysisSkill(),
    "hypothesis_gen":        HypothesisGenSkill(),
    "statistical_analysis":  StatisticalAnalysisSkill(),
    "credibility_score":     CredibilityScoreSkill(),
    "fallback_router":       FallbackRouterSkill(),
    "meta_analysis":         MetaAnalysisSkill(),
    "sentiment_cluster":     SentimentClusterSkill(),
    # Tier 3 — Output
    "report_generator":  ReportGeneratorSkill(),
    "exec_summary":      ExecSummarySkill(),
    "bibliography_gen":  BibliographyGenSkill(),
    "decision_matrix":   DecisionMatrixSkill(),
    "explainer":         ExplainerSkill(),
    "annotation_gen":    AnnotationGenSkill(),
    "visualization_spec":VisualizationSpecSkill(),
    "knowledge_delta":   KnowledgeDeltaSkill(),
}
