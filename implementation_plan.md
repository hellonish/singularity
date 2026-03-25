# Universal Research Agent — Complete Implementation Plan

## Context

This document is the authoritative specification for building a universal,
domain-adaptive research AI agent. The Planner layer (orchestrator, skill routing,
domain detection, DAG execution, replan loop) already exists across five files:

- `PLANNER_SKILL.md` — LLM system prompt for the Planner
- `DOMAIN_REGISTRY.json` — 11 domain bundles, 44-skill registry, fallback chains
- `ROBUSTNESS.md` — retry policy, degradation rules, escalation logic
- `orchestrator.py` — full async orchestrator with FallbackRouter, credibility scoring,
  cycle detection, topological wave execution
- `example_plan.md` — hand-written example DAG output

**This plan covers everything that must be built next:** the tool layer, skill I/O
contracts, all 44 skill implementations, citation tracker, context budget manager,
and test harness.

---

## Architectural Decisions (Locked)

These were decided before this plan was written. Do not revisit.

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Web search provider | Free-first (DuckDuckGo → Tavily fallback) | Cost minimisation; paid fallback for reliability |
| Academic search | arXiv SDK + Semantic Scholar API (both free) | Free, authoritative, well-documented |
| Skill execution model | Hybrid | Retrieval = deterministic Python; Analysis + Output = LLM-based |
| Citation ID format | Author-year `[Smith2024]` | Human-readable, standard in academic writing |
| LLM for analysis/output skills | `claude-sonnet-4-20250514` (regular, not reasoning) | Instruction-following, format-compliant, cost-efficient |
| LLM for Planner | Reasoning model recommended (`claude-opus-4-5` or equivalent) | Single high-stakes call; correctness over speed |

---

## Repository Structure

Legend: `✅ exists` | `🔨 Phase 0A` | `📋 Phase 0B` | `1️⃣ Phase 1` | `2️⃣ Phase 2` | `3️⃣ Phase 3` | `🧪 Phase 4`

```
singularity/                            ← project root
├── implementation_plan.md              ← this file ✅
│
├── SKILLS/                             ← existing ✅
│   └── PLANNER.md                      ← LLM system prompt for the Planner
│
├── llm/                                ← existing — LLM client abstraction ✅
│   ├── base.py                         ← BaseLLMClient interface
│   ├── grok.py                         ← GrokClient (xAI / Grok models)
│   ├── deepseek.py                     ← DeepSeekClient
│   ├── gemini.py                       ← GeminiClient
│   └── router.py                       ← LLM router (model selection)
│
├── planner/                            ← existing — domain knowledge ✅
│   ├── __init__.py
│   └── domain_registry.json            ← 11 domain bundles, 44-skill registry, fallback chains
│
├── orchestrator/                       ← existing — async DAG orchestrator ✅
│   ├── __init__.py                     ← exports run_orchestrator
│   ├── config.py                       ← constants, paths, model names
│   ├── models.py                       ← PlanNode, PlanMetadata, Plan, GapItem, enums
│   ├── context.py                      ← ExecutionContext
│   ├── domain.py                       ← DomainRegistry
│   ├── planner.py                      ← parse_plan + Planner class
│   ├── skills.py                       ← SkillBase + all skill stubs + SKILL_REGISTRY
│   ├── executor.py                     ← FallbackRouter + wave/node execution
│   ├── runner.py                       ← run_orchestrator + gap/termination/loop logic
│   └── orchestrator.py                 ← CLI entry point
│
├── tools/                              ← Phase 0A: tool abstraction layer 🔨
│   ├── __init__.py                     ← exports all tool classes
│   ├── base.py                         ← ToolBase, ToolResult dataclass
│   ├── web_fetch.py                    ← DuckDuckGo primary + Tavily fallback
│   ├── arxiv_api.py                    ← arxiv Python SDK
│   ├── pubmed_api.py                   ← Biopython Entrez (NCBI_EMAIL required)
│   ├── semantic_scholar.py             ← Semantic Scholar REST API (free)
│   ├── github_api.py                   ← PyGithub (GITHUB_TOKEN optional)
│   ├── sec_edgar.py                    ← EDGAR full-text search REST API
│   ├── courtlistener.py                ← CourtListener REST API (free, no auth)
│   ├── clinicaltrials.py               ← ClinicalTrials.gov v2 REST API (free)
│   ├── standards_fetch.py              ← NIST CSF + IEEE Xplore (free tier)
│   ├── youtube_transcript.py           ← youtube-transcript-api (free)
│   ├── google_books.py                 ← Google Books API (GOOGLE_BOOKS_API_KEY optional)
│   ├── dataset_hub.py                  ← HuggingFace Hub API (free)
│   ├── pdf_reader.py                   ← pdfplumber primary + PyMuPDF fallback
│   └── translation.py                  ← LibreTranslate primary + Google Translate fallback
│
├── contracts/                          ← Phase 0B: skill I/O contracts 📋
│   ├── __init__.py
│   └── skill_contracts.py              ← SourceRecord, RetrievalOutput, AnalysisOutput, etc.
│
├── citations/                          ← Phase 1 utility 1️⃣
│   ├── __init__.py
│   └── registry.py                     ← CitationRegistry, CitationRecord
│
├── context/                            ← Phase 3 utility 3️⃣
│   ├── __init__.py
│   └── budget.py                       ← ContextBudgetManager
│
├── skills/                             ← Phases 1-3: real skill implementations
│   ├── base.py                         ← re-exports SkillBase from orchestrator.skills
│   │
│   ├── tier1_retrieval/                ← Phase 1: 18 skill files 1️⃣
│   │   ├── __init__.py
│   │   ├── web_search.py
│   │   ├── academic_search.py
│   │   ├── clinical_search.py
│   │   ├── legal_search.py
│   │   ├── financial_search.py
│   │   ├── news_archive.py
│   │   ├── gov_search.py
│   │   ├── code_search.py
│   │   ├── patent_search.py
│   │   ├── standards_search.py
│   │   ├── forum_search.py
│   │   ├── video_search.py
│   │   ├── dataset_search.py
│   │   ├── book_search.py
│   │   ├── social_search.py
│   │   ├── pdf_deep_extract.py
│   │   ├── multimedia_search.py
│   │   └── data_extraction.py
│   │
│   ├── tier2_analysis/                 ← Phase 2: 18 skill files 2️⃣
│   │   ├── __init__.py
│   │   ├── synthesis.py
│   │   ├── comparative_analysis.py
│   │   ├── gap_analysis.py
│   │   ├── quality_check.py
│   │   ├── translation.py
│   │   ├── entity_extraction.py
│   │   ├── timeline_construct.py
│   │   ├── citation_graph.py
│   │   ├── contradiction_detect.py
│   │   ├── claim_verification.py
│   │   ├── trend_analysis.py
│   │   ├── causal_analysis.py
│   │   ├── hypothesis_gen.py
│   │   ├── statistical_analysis.py
│   │   ├── credibility_score.py
│   │   ├── fallback_router.py
│   │   ├── meta_analysis.py
│   │   └── sentiment_cluster.py
│   │
│   └── tier3_output/                   ← Phase 3: 8 skill files 3️⃣
│       ├── __init__.py
│       ├── report_generator.py
│       ├── exec_summary.py
│       ├── bibliography_gen.py
│       ├── decision_matrix.py
│       ├── explainer.py
│       ├── annotation_gen.py
│       ├── visualization_spec.py
│       └── knowledge_delta.py
│
├── prompts/                            ← LLM system prompts for analysis + output skills
│   ├── synthesis.md
│   ├── comparative_analysis.md
│   ├── gap_analysis.md
│   ├── quality_check.md
│   ├── contradiction_detect.md
│   ├── claim_verification.md
│   ├── causal_analysis.md
│   ├── statistical_analysis.md
│   ├── meta_analysis.md
│   ├── trend_analysis.md
│   ├── timeline_construct.md
│   ├── hypothesis_gen.md
│   ├── entity_extraction.md
│   ├── citation_graph.md
│   ├── sentiment_cluster.md
│   ├── report_generator.md
│   ├── exec_summary.md
│   ├── explainer.md
│   ├── decision_matrix.md
│   ├── bibliography_gen.md
│   ├── annotation_gen.md
│   ├── visualization_spec.md
│   └── knowledge_delta.md
│
└── tests/                              ← Phase 4 🧪
    ├── mock_context.py                 ← MockContextBuilder
    ├── skill_runner.py                 ← SingleSkillRunner
    ├── test_retrieval.py               ← Phase 1 skill tests
    ├── test_analysis.py                ← Phase 2 skill tests
    ├── test_output.py                  ← Phase 3 skill tests
    └── test_integration.py            ← end-to-end mini-DAG tests
```

---

## Dependencies

```toml
# pyproject.toml or requirements.txt

# Core
anthropic>=0.40.0
asyncio                     # stdlib

# Tools — free tier
duckduckgo-search>=6.0.0    # web_search primary
arxiv>=2.1.0                # arxiv_api
biopython>=1.84             # pubmed_api (Entrez)
PyGithub>=2.3.0             # github_api
sec-edgar-downloader>=5.0.0 # sec_edgar
requests>=2.31.0            # courtlistener, clinicaltrials, semantic_scholar
youtube-transcript-api>=0.6.2  # video_search
google-api-python-client>=2.0.0  # google_books
huggingface-hub>=0.23.0     # dataset_hub

# Tools — paid fallback (optional, set via env vars)
tavily-python>=0.3.0        # web_fetch paid fallback

# PDF
pdfplumber>=0.11.0
PyMuPDF>=1.24.0             # fitz

# Translation (free self-hosted or API)
# LibreTranslate via requests — no SDK needed

# Utilities
pydantic>=2.7.0             # schema validation for contracts
python-dotenv>=1.0.0        # env var management
aiohttp>=3.9.0              # async HTTP for tools
tenacity>=8.3.0             # retry logic
```

---

## Phase 0A — Tool Abstraction Layer

### `tools/base.py`

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ToolResult:
    content: str                    # primary extracted text / summary
    sources: list[dict]             # list of {title, url, date, snippet}
    credibility_base: float         # 0-1 baseline before adjustments
    raw: Any = None                 # raw API response (for debugging)
    error: str | None = None        # set if tool failed

class ToolBase:
    name: str = "base"
    
    async def call(self, query: str, **kwargs) -> ToolResult:
        raise NotImplementedError
    
    async def call_with_retry(self, query: str, max_retries: int = 2, **kwargs) -> ToolResult:
        # Uses tenacity for retry logic with exponential backoff
        # Returns ToolResult(error=...) after exhausting retries — never raises
        raise NotImplementedError
```

### Tool implementation notes

**`tools/web_fetch.py`**
- Primary: `duckduckgo_search` — `DDGS().text(query, max_results=10)`
- Fallback: Tavily client — only activated if `TAVILY_API_KEY` env var is set AND
  DuckDuckGo returns 0 results or raises `RatelimitException`
- `credibility_base`: 0.75 for general web, 0.85 for `.gov`/`.edu` domains
- Strip JavaScript-rendered content — use `aiohttp` for raw HTML + BeautifulSoup for
  text extraction

**`tools/arxiv_api.py`**
- `arxiv.Search(query=query, max_results=10, sort_by=arxiv.SortCriterion.Relevance)`
- Extract: title, authors, abstract, arxiv_id, published date, pdf_url
- `credibility_base`: 0.88 for preprints, 0.95 if journal field is populated
- Filter by date using `node.recency_window_years` passed as kwarg

**`tools/pubmed_api.py`**
- `Entrez.esearch(db="pubmed", term=query, retmax=10)` then `Entrez.efetch`
- Extract: PMID, title, authors, abstract, journal, pub_date, MeSH terms
- `credibility_base`: 0.92 for peer-reviewed, 0.85 for preprints (biorxiv)
- Requires `NCBI_EMAIL` env var (free, no key needed)

**`tools/semantic_scholar.py`**
- REST: `https://api.semanticscholar.org/graph/v1/paper/search`
- Free tier: 100 requests/5min unauthenticated, 1 req/sec
- Fields: `title,authors,year,abstract,citationCount,openAccessPdf`
- `credibility_base`: 0.90; boost to 0.95 if `citationCount > 50`

**`tools/courtlistener.py`**
- REST: `https://www.courtlistener.com/api/rest/v4/search/?q={query}&type=o`
- Free, no auth required for basic search
- Extract: case_name, court, date_filed, citation, absolute_url
- `credibility_base`: 0.95

**`tools/clinicaltrials.py`**
- REST v2: `https://clinicaltrials.gov/api/v2/studies?query.term={query}`
- Free, no auth
- Extract: NCT_id, title, status, phase, conditions, interventions, results_url
- `credibility_base`: 1.0 (official registry)

**`tools/pdf_reader.py`**
- `pdfplumber.open(path_or_bytes)` for text extraction
- `fitz` (PyMuPDF) for page rendering if pdfplumber fails on scanned PDFs
- Extract: full text, tables (as list of lists), page count, metadata
- Chunking: split into 2000-token chunks, return as list with page numbers

**`tools/translation.py`**
- Primary: LibreTranslate (`https://libretranslate.com/translate`) — free, self-hostable
- Fallback: `GOOGLE_TRANSLATE_API_KEY` env var if set
- Always returns: `{original, translated, source_lang, target_lang, confidence}`
- Confidence < 0.8 → flag as `[low-confidence translation]` in output

**`tools/github_api.py`**
- `Github(os.getenv("GITHUB_TOKEN"))` — token optional but increases rate limit
- `g.search_repositories(query, sort="stars")` for repo discovery
- For each repo: fetch README via `repo.get_readme()`, last commit date, stars, language
- `credibility_base`: 0.70 base, boost by `min(0.25, stars/1000 * 0.25)`

**`tools/sec_edgar.py`**
- `sec_edgar_downloader.Downloader` for 10-K, 10-Q, 8-K filings
- EDGAR full-text search: `https://efts.sec.gov/LATEST/search-index?q={query}`
- Extract: company, form_type, filing_date, accession_number, document_url
- `credibility_base`: 1.0 (official regulatory filing)

**`tools/standards_fetch.py`**
- NIST: `https://csrc.nist.gov/CSRC/media/publications/` + search
- IEEE Xplore: `https://ieeexploreapi.ieee.org/api/v1/search/articles` (free tier)
- `credibility_base`: 1.0

**`tools/youtube_transcript.py`**
- `YouTubeTranscriptApi.get_transcript(video_id)` from `youtube_transcript_api`
- Search via DuckDuckGo with `site:youtube.com` prefix to find relevant video IDs
- Combine transcript chunks into time-indexed text
- `credibility_base`: 0.65 for general YouTube, 0.80 for conference/academic channels

**`tools/google_books.py`**
- `https://www.googleapis.com/books/v1/volumes?q={query}` — free, no key needed for
  basic search (rate limited); `GOOGLE_BOOKS_API_KEY` for higher limits
- Extract: title, authors, publishedDate, description, previewLink
- `credibility_base`: 0.85 for published books

**`tools/dataset_hub.py`**
- `huggingface_hub.list_datasets(search=query, limit=10)`
- Extract: dataset_id, author, description, tags, downloads, last_modified
- `credibility_base`: 0.80; boost to 0.90 if author is an institution

---

## Phase 0B — Skill I/O Contracts

### `contracts/SKILL_CONTRACTS.py`

This file defines the frozen input/output schema for every skill. All skill
implementations and all test harness code import from here. If a schema needs to
change, it changes here and all consumers update.

**Common source record** (produced by all tier 1 retrieval skills):

```python
@dataclass
class SourceRecord:
    citation_id: str           # assigned by CitationRegistry: [Smith2024]
    title: str
    url: str
    snippet: str               # 200-300 char extract
    date: str | None           # ISO format YYYY-MM-DD
    source_type: str           # "academic" | "web" | "gov" | "forum" | "legal" |
                               # "clinical" | "financial" | "code" | "book" |
                               # "video" | "standard" | "patent" | "dataset"
    credibility_base: float    # 0-1 from tool layer
    authors: list[str]         # for academic / legal / books
    metadata: dict             # skill-specific extra fields
```

**Retrieval skill output** (all 18 tier 1 skills write this to `output_slot`):

```python
@dataclass
class RetrievalOutput:
    sources: list[SourceRecord]
    query_used: str
    result_count: int
    coverage_notes: str        # e.g. "6 results found; 2 excluded for recency"
    fallback_used: bool        # True if primary tool failed
    skill_name: str
```

**Analysis skill output** (base — each skill extends this):

```python
@dataclass
class AnalysisOutput:
    skill_name: str
    summary: str               # 2-4 sentence human-readable summary
    findings: list[dict]       # skill-specific structured findings
    citations_used: list[str]  # list of citation_ids referenced
    confidence: float          # 0-1 overall confidence in the analysis
    coverage_gaps: list[str]   # what this analysis could not address
    upstream_slots_consumed: list[str]
```

**Quality check output**:

```python
@dataclass
class QualityReport:
    node_id: str
    axes_evaluated: list[str]
    results: dict[str, AxisResult]   # axis_name → AxisResult
    overall_pass: bool
    overall_score: float
    remediation_suggestion: str | None

@dataclass
class AxisResult:
    axis: str
    passed: bool
    score: float               # 0-1
    reason: str
    threshold: float           # what score was needed to pass
```

**Output skill output**:

```python
@dataclass
class OutputDocument:
    skill_name: str
    format: str                # "report" | "exec_summary" | "explainer" | etc.
    content: str               # final rendered text
    audience: str
    word_count: int
    citations_included: list[str]    # citation_ids present in content
    coverage_gaps_disclosed: list[str]   # node_ids that were partial/failed
    disclaimer_present: bool
    language: str
```

---

## Phase 1 — Citation Tracker

### `citations/registry.py`

The `CitationRegistry` is instantiated inside `ExecutionContext` and shared
across all nodes. Retrieval skills register sources here. Analysis and output
skills reference sources by `citation_id` only — never by raw URL.

```python
@dataclass
class CitationRecord:
    citation_id: str           # [Smith2024], [Smith2024a] if collision
    title: str
    authors: list[str]
    year: str | None
    url: str
    source_type: str
    credibility_base: float
    registered_by: str         # skill name that registered this source
    registered_at_slot: str    # output_slot of the node that found it

class CitationRegistry:
    def register(self, source: SourceRecord, registered_by: str,
                 output_slot: str) -> str:
        # Generates citation_id from first author surname + year
        # Handles collisions: [Smith2024], [Smith2024a], [Smith2024b]
        # Returns the assigned citation_id
        
    def get(self, citation_id: str) -> CitationRecord | None:
        
    def all(self) -> list[CitationRecord]:
    
    def by_slot(self, output_slot: str) -> list[CitationRecord]:
    
    def format_bibliography(self, style: str, ids: list[str]) -> str:
        # style: "APA" | "Bluebook" | "IEEE" | "Vancouver"
```

**Citation ID generation rules:**
- Format: `[AuthorYYYY]` using first author's surname + publication year
- If no author: use first 3 words of title, CamelCased
- Collision handling: append `a`, `b`, `c` — e.g. `[Smith2024a]`
- If no year: use `[AuthorND]` (no date)
- All IDs stored in a `dict[citation_id → CitationRecord]` for O(1) lookup

---

## Phase 1 — Retrieval Skill Implementations

### Execution model: deterministic Python

All 18 tier 1 retrieval skills follow this pattern:

```python
class WebSearchSkill(SkillBase):
    name = "web_search"
    
    async def run(self, node: PlanNode, ctx: ExecutionContext,
                  client: anthropic.Anthropic,
                  registry: DomainRegistry) -> tuple[Any, NodeStatus, float]:
        
        # 1. Call tool
        tool = WebFetchTool()
        result = await tool.call_with_retry(node.description)
        
        if result.error:
            return self._empty_result(node, result.error), NodeStatus.FAILED, 0.0
        
        # 2. Filter by acceptance axes
        sources = self._filter_by_axes(result.sources, node.acceptance, node)
        
        # 3. Register all sources in CitationRegistry
        for src in sources:
            citation_id = ctx.citation_registry.register(
                src, registered_by=self.name, output_slot=node.output_slot)
            src["citation_id"] = citation_id
        
        # 4. Build output matching RetrievalOutput contract
        output = RetrievalOutput(
            sources=sources,
            query_used=result.content,
            result_count=len(sources),
            coverage_notes=self._coverage_notes(sources, node),
            fallback_used=result.raw.get("fallback_used", False),
            skill_name=self.name,
        )
        
        # 5. Determine status
        status = NodeStatus.OK if len(sources) >= 2 else NodeStatus.PARTIAL
        credibility = sum(s.credibility_base for s in sources) / max(len(sources), 1)
        
        return output.__dict__, status, credibility
```

### Per-skill implementation notes

**`web_search`**
- Tool: `WebFetchTool` (DuckDuckGo → Tavily fallback)
- Authority filter: no filter — all public web sources accepted
- Recency filter: apply `node.recency_window_years` if `recency` in `node.acceptance`
- Min sources for `OK`: 3; fewer → `PARTIAL`

**`academic_search`**
- Tools: `ArxivTool` + `SemanticScholarTool` — query both, deduplicate by title similarity
- Authority filter: arXiv + Semantic Scholar + DOI-bearing results only
- Recency filter: always applied — defaults to domain recency window
- Min sources for `OK`: 2 papers

**`clinical_search`**
- Tools: `PubmedTool` + `ClinicalTrialsTool`
- Authority filter: PubMed, Cochrane, ClinicalTrials.gov only
- Special: extract trial phase (I/II/III/IV) and RCT flag into `metadata`
- Min sources for `OK`: 2; one must be a trial or systematic review

**`legal_search`**
- Tool: `CourtListenerTool`
- HARD RULE: jurisdiction check — if `jurisdiction_relevance` in `node.acceptance`,
  filter out results from wrong jurisdiction. If 0 results remain → `FAILED`, do NOT
  fall back to web search for legal conclusions (see ROBUSTNESS.md)
- Min sources for `OK`: 1 primary case or statute

**`financial_search`**
- Tool: `SecEdgarTool` for filings; `WebFetchTool` with financial site filter for news
- Authority hierarchy: SEC filings (1.0) > earnings call transcripts (0.90) > 
  financial news (0.80) > analyst blogs (0.65)
- Extract: ticker symbol, fiscal period, filing type into `metadata`

**`gov_search`**
- Tool: `WebFetchTool` filtered to `.gov` domains
- DuckDuckGo query: append `site:*.gov` or `site:*.gov.*` for non-US
- `credibility_base`: 0.95

**`news_archive`**
- Tool: `WebFetchTool` filtered to known news domains
  (reuters.com, apnews.com, bbc.com, nytimes.com, wsj.com, ft.com, etc.)
- Extract: author, publication, date, headline separately into `metadata`
- `credibility_base`: 0.80

**`code_search`**
- Tool: `GitHubTool`
- Query parsed for: language filter, repo name hints, topic tags
- Extract README first 1500 chars, last commit date, stars, license
- `credibility_base`: base 0.70, stars-adjusted up to 0.90

**`forum_search`**
- Tool: `WebFetchTool` filtered to SO, Reddit, HN, domain-specific forums
- `credibility_base`: 0.60 (SO accepted answers: 0.70)
- Accept votes/upvotes into `metadata` as signal

**`pdf_deep_extract`**
- Tool: `PdfReaderTool`
- Input: the node description must contain a URL or local path to the PDF
- If URL: fetch bytes first via `aiohttp`, then pass to pdfplumber
- Returns: chunked text + table list + page metadata

**`dataset_search`**
- Tool: `DatasetHubTool`
- Extract: task_categories, language, size_categories, license, downloads

**`standards_search`**
- Tool: `StandardsFetchTool`
- Extract: standard_number, version, issuing_body, publication_date
- `credibility_base`: 1.0

**`video_search`**, **`book_search`**, **`social_search`**, **`multimedia_search`**,
**`patent_search`** — follow the same pattern as `web_search` with their respective
tools and credibility adjustments from `DOMAIN_REGISTRY.json`.

**`data_extraction`**
- Tool: `PdfReaderTool` + HTML table parser (BeautifulSoup)
- Used for structured data extraction from tables in PDFs or web pages
- Output: list of extracted tables as `list[list[str]]` + source citation

**`translation`** (retrieval-tier utility)
- Tool: `TranslationTool`
- Called from orchestrator when `multilingual: true` in plan metadata
- Wraps upstream retrieval results: translates snippet + title
- Appends `[translated: {src_lang} → {tgt_lang}]` to source metadata

---

## Phase 2 — Quality Axes Skill

This is the most critical skill in tier 2. All other analysis skills depend on
being able to pass their output through quality_check before synthesis.

### `skills/tier2_analysis/quality_check.py`

Execution model: **LLM-based** — uses `claude-sonnet-4-20250514`

System prompt location: `prompts/quality_check.md`

```python
class QualityCheckSkill(SkillBase):
    name = "quality_check"
    
    async def run(self, node, ctx, client, registry):
        # 1. Identify which upstream output to evaluate
        #    The node being quality-checked is named in node.description
        #    e.g. "Evaluate node n3 output against its acceptance axes"
        
        # 2. Load the target node's output from ctx.results
        
        # 3. Load the target node's acceptance axes from the plan
        #    (stored in ctx.plan_snapshot set by orchestrator)
        
        # 4. Call LLM with quality_check.md prompt
        
        # 5. Parse structured QualityReport from response
        
        # 6. If overall_pass is False: the orchestrator gap analyser 
        #    automatically adds a GapItem using remediation_suggestion
```

### `prompts/quality_check.md`

```markdown
# QUALITY CHECK SKILL

You evaluate whether a research node's output satisfies its assigned
acceptance criteria. You produce a structured report — one score per axis.

## Input you receive
- node_output: the dict produced by the node being evaluated
- acceptance_axes: list of axis labels this node must satisfy
- domain: the research domain for domain-specific axis interpretation
- node_description: what the node was supposed to do

## Scoring rubric — universal axes

**factual_grounding**
Pass if: ≥80% of claims in the output have a corresponding citation_id
         in the citations_used list and that citation exists in the registry.
Score: (cited_claims / total_claims). Threshold: 0.80

**source_authority**
Pass if: ≥70% of sources in citations_used have credibility_base ≥ 0.80
         OR the domain rubric notes allow lower (e.g. forum_search).
Score: weighted avg credibility. Threshold: domain-specific (see below)

**coverage**
Pass if: the output's summary and findings address all aspects named in
         node_description. Score: 0-1 based on aspect match. Threshold: 0.75

**recency**
Pass if: ≥80% of sources have date within the plan's recency_window_years.
Score: proportion within window. Threshold: 0.80

**cross_validation**
Pass if: key claims appear in ≥2 independent citations from different domains.
Score: proportion of key claims with ≥2 sources. Threshold: 0.70

**relevance**
Pass if: the output directly addresses the node_description and does not
         include irrelevant tangents >20% of content.
Score: 0-1. Threshold: 0.80

**coherence**
Pass if: the output does not contradict any previously completed nodes in
         ctx (passed as context summaries). Score: 0-1. Threshold: 0.90

**depth**
Pass if: the output contains sufficient technical detail for the domain.
         "Sufficient" is domain-calibrated — see domain thresholds.
Score: 0-1. Threshold: domain-specific

## Scoring rubric — domain-specific axes

**jurisdiction_relevance** (legal)
Pass if: all case citations are from the jurisdiction named in node metadata.
Score: proportion from correct jurisdiction. Threshold: 1.0 (hard)

**clinical_significance** (medical)
Pass if: quantitative outcomes include effect size + confidence interval,
         not just p-value. Score: 0 or 1 per outcome. Threshold: 1.0 (hard)

**replication_status** (science)
Pass if: output notes whether findings have been independently replicated.
Score: 0 (not mentioned) / 0.5 (mentioned without verdict) / 1.0. Threshold: 0.5

**methodological_soundness** (research/medical/policy)
Pass if: study design is appropriate for the claim type (RCT for causal
         claims, not just observational). Score: 0-1. Threshold: 0.75

**conflict_of_interest** (journalism/medical/finance)
Pass if: funding sources and affiliations for all primary sources are
         either disclosed or verified as absent. Score: 0 or 1. Threshold: 1.0

**temporal_validity** (legal/policy/engineering/market)
Pass if: all cited sources reflect current state — no superseded laws,
         outdated standards, or stale market data. Score: 0-1. Threshold: 0.85

**geographic_scope** (legal/policy/market/product)
Pass if: findings are scoped to the correct geography and do not
         generalise across regions without basis. Score: 0-1. Threshold: 0.80

**audience_calibration** (general/product)
Pass if: language complexity matches the stated audience level.
Score: 0-1. Threshold: 0.80

## Output format — respond ONLY with this JSON, no prose

{
  "node_id": "...",
  "axes_evaluated": ["..."],
  "results": {
    "axis_name": {
      "passed": true,
      "score": 0.0,
      "reason": "one sentence",
      "threshold": 0.0
    }
  },
  "overall_pass": true,
  "overall_score": 0.0,
  "remediation_suggestion": "null or one sentence on how to fix"
}
```

---

## Phase 2 — Analysis Skill Implementations

### Execution model: LLM-based for all tier 2 skills

All analysis skills follow this pattern:

```python
class SynthesisSkill(SkillBase):
    name = "synthesis"
    PROMPT_PATH = Path("prompts/synthesis.md")
    
    async def run(self, node, ctx, client, registry):
        # 1. Load prompt
        system_prompt = self.PROMPT_PATH.read_text()
        
        # 2. Build user message from upstream context
        #    Use ContextBudgetManager to control size
        budget_mgr = ContextBudgetManager()
        upstream_context = budget_mgr.build_context(node, ctx)
        
        # 3. LLM call
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": upstream_context}]
        )
        
        # 4. Parse response into AnalysisOutput contract
        output = self._parse(response.content[0].text, node)
        
        # 5. Status and credibility
        status = NodeStatus.OK if output.confidence >= 0.70 else NodeStatus.PARTIAL
        return output.__dict__, status, output.confidence
```

### Prompt file structure (all analysis prompts follow this template)

Each file in `prompts/` for analysis skills:

```markdown
# {SKILL_NAME} SKILL

## Role
One sentence: what this skill does.

## Input you receive
Description of the upstream context structure it receives.
Which output_slots it reads and what schema to expect (AnalysisOutput or RetrievalOutput).

## Task instructions
Step-by-step, precise instructions for how to perform the analysis.
What to look for, what to ignore, how to handle missing data.

## Handling insufficient upstream data
What to return if upstream sources are empty or low-quality.
Never return an empty findings list — always return a finding that describes the gap.

## Output format — respond ONLY with this JSON, no prose
{
  "summary": "2-4 sentence summary",
  "findings": [...],         ← skill-specific structure defined here
  "citations_used": ["[Smith2024]", ...],
  "confidence": 0.0,
  "coverage_gaps": ["..."],
  "upstream_slots_consumed": ["..."]
}
```

### Key analysis skill prompt notes

**`synthesis.md`**
- Receives: all upstream slot summaries + synthesis_hint from node
- Must follow synthesis_hint strictly for audience calibration
- Findings: list of `{claim, supporting_citations, confidence, hedging_note}`
- Must not introduce claims not present in upstream sources

**`comparative_analysis.md`**
- Receives: 2+ upstream slots to compare
- Extracts comparison axes from node.description
- Findings: structured table `{axis, values_per_subject, winner_if_any, caveat}`
- Explicitly notes when data is insufficient to compare on a given axis

**`contradiction_detect.md`**
- Receives: multiple upstream slots
- For each pair of sources that disagree: `{claim, source_a, source_b, contradiction_type, severity}`
- `contradiction_type`: "factual" | "methodological" | "interpretive"
- Does NOT resolve contradictions — only flags them with evidence

**`causal_analysis.md`**
- Hardest analysis skill. Receives synthesis or comparative output
- Must explicitly distinguish: correlation / association / causal claim
- For each causal claim: `{claim, evidence_type, confounders_noted, strength}`
- `evidence_type`: "RCT" | "observational" | "mechanistic" | "expert_opinion"
- If no RCT evidence exists for a causal claim: mandatory note in findings

**`statistical_analysis.md`**
- Receives: data_extraction or retrieval output containing tables or numbers
- Extracts numerical values with units
- Computes: mean, median, range, N where possible from extracted data
- Never fabricates statistics — if data is insufficient, states it explicitly

**`meta_analysis.md`**
- Medical domain only. Receives: clinical_search + statistical_analysis outputs
- Aggregates effect sizes using fixed/random effects logic described in prompt
- Outputs: pooled effect estimate + heterogeneity measure (I²) + forest plot data
- If < 3 studies: returns `{insufficient_studies: true}` not a pooled estimate

**`claim_verification.md`**
- Receives: synthesis or comparative output + retrieval outputs
- For each key claim in synthesis: verifies against source citations
- `{claim, verified: bool, supporting_sources: [], contradicting_sources: [], verdict}`

**`gap_analysis.md`**
- Receives: all completed node outputs
- Compares against node.description scope + termination_signal from plan metadata
- Outputs: `{gap_description, affected_scope, severity: "critical|moderate|minor", suggested_node}`
- `suggested_node` is used by Planner in replan to add targeted new nodes

---

## Phase 3 — Context Budget Manager

### `context/budget.py`

Analysis and output skills receive upstream context. Without budgeting, deep DAGs
(9+ nodes) will overflow the LLM context window.

```python
class ContextBudgetManager:
    MAX_DIRECT_DEP_TOKENS = 3000    # full content for direct dependencies
    MAX_INDIRECT_DEP_TOKENS = 350   # summary only for indirect
    MAX_TOTAL_TOKENS = 8000         # hard cap for entire upstream context
    
    def build_context(self, node: PlanNode, ctx: ExecutionContext) -> str:
        """
        Builds the upstream context string passed to the LLM.
        Direct dependencies (in node.depends_on): full content up to 3000 tokens each
        Indirect (all other resolved slots): 350-char summary only
        Hard cap: truncate least-relevant slots if total exceeds 8000 tokens
        """
```

Strategy:
- Direct dependency slots: pass full `RetrievalOutput` or `AnalysisOutput` JSON
- Indirect slots: pass only `summary` field (2-4 sentences)
- If total still exceeds cap: drop indirect slots by inverse credibility score
  (drop least credible first)
- Synthesis hint from `node.synthesis_hint` always included regardless of budget

---

## Phase 3 — Output Skill Implementations

### Execution model: LLM-based

All output skills use the same pattern as analysis skills. Key differences:

**`report_generator.md` — required sections (in order):**
1. Executive summary (150 words max)
2. Methodology note (what was searched, what was found, what tools were used)
3. Findings (one section per major theme from synthesis output)
4. Limitations (coverage gaps disclosed here — mandatory, from `ctx.node_status`)
5. References (inline `[Smith2024]` format throughout; full list at end from CitationRegistry)

**Audience length targets:**
- `layperson`: 600 words total, no inline citations visible (footnotes only)
- `student`: 1500 words, full citations, methodology section included
- `practitioner`: 2000 words, full citations, technical detail
- `expert`: 3000+ words, full citations, GRADE-style evidence levels for medical
- `executive`: 400 words, BLUF first, no methodology section, decision framed in
  paragraph 1

**`exec_summary.md` — structure:**
- Line 1: Bottom line (the answer or recommendation in one sentence)
- Key evidence: 3 bullet points maximum
- Limitations: one bullet
- Next step or decision: one sentence
- Maximum 350 words enforced in prompt

**`explainer.md` — rules:**
- Detect and replace jargon: the prompt instructs the LLM to identify technical
  terms and provide plain-language equivalents in parentheses on first use
- Use one analogy per major concept
- No citations visible in body text — aggregate as "according to researchers" or
  "studies show" with footnote markers
- Reading level: ~8th grade for `layperson`, ~12th grade for `student`

**`decision_matrix.md`**
- Reads `comparative_analysis` output slot for axes and values
- Produces: structured options table + conditional recommendation
- Format: markdown table + one paragraph recommendation with explicit conditions
- Never produces unconditional "you should do X" — always "if [condition], then [X]"
- Sensitivity disclaimer mandatory for medical/legal/financial output

**`bibliography_gen.md`**
- Reads `CitationRegistry.all()` filtered to `citations_used` list
- Citation styles:
  - `academic_paper` / `systematic_review` / `general`: APA 7th edition
  - `legal_brief`: Bluebook 21st edition
  - `technical_report`: IEEE
  - `systematic_review` (medical): Vancouver/NLM
- If a citation is missing required fields (no author, no date): formats as best
  possible and appends `[incomplete citation — verify manually]`

**`annotation_gen.md`**
- One entry per source in `citations_used`
- Format: `[Smith2024] Title. Author(s). Date. ↳ [2-3 sentence critical note]`
- Critical note must address: what this source contributes, its authority level,
  and any limitations (sample size, jurisdiction, recency, funding)

**`visualization_spec.md`**
- Does NOT produce a chart — produces a machine-readable spec
- Output schema:
  ```json
  {
    "chart_type": "bar|line|scatter|table|timeline|heatmap",
    "title": "...",
    "x_axis": {"label": "...", "values": [...]},
    "y_axis": {"label": "...", "values": [...]},
    "series": [...],
    "notes": "..."
  }
  ```
- Downstream rendering is the caller's responsibility

**`knowledge_delta.md`**
- Requires `prior_date` in plan metadata (ISO format)
- Compares current findings against a prior state description
- Output: `{new_developments: [], changed_positions: [], deprecated_claims: []}`

---

## Phase 3 — Sensitivity Disclaimer Node

When `sensitivity_flag: true` in plan metadata (medical, legal, finance domains),
the Planner adds a mandatory disclaimer node as the final output node.

This node uses `exec_summary` skill with a fixed `synthesis_hint`:

```
"Prepend the following disclaimer to the output, verbatim:
DISCLAIMER: This document is for informational purposes only. It does not
constitute [medical advice / legal advice / financial advice]. All findings
should be verified by a qualified [physician / attorney / financial advisor]
before acting upon them. The research agent cannot account for individual
circumstances, jurisdiction-specific requirements, or events after the
research was conducted."
```

This is non-negotiable and must appear at the top of all sensitive domain outputs.

---

## Phase 4 — Test Harness

### `tests/mock_context.py`

```python
class MockContextBuilder:
    """
    Builds a pre-populated ExecutionContext from SKILL_CONTRACTS.py
    schemas. Used to test skills in isolation.
    
    Usage:
        ctx = MockContextBuilder().with_retrieval_output(
            slot="bm25_papers",
            source_count=5,
            source_type="academic",
            credibility=0.90
        ).build()
        
        # Then run any analysis skill against this ctx
    """
```

### `tests/skill_runner.py`

```python
class SingleSkillRunner:
    """
    Runs one skill against a mock context. Validates that the output
    matches SKILL_CONTRACTS.py schema before returning.
    
    Usage:
        result = await SingleSkillRunner().run(
            skill=SynthesisSkill(),
            node=PlanNode(node_id="n1", skill="synthesis", ...),
            ctx=mock_ctx
        )
        assert result.status == NodeStatus.OK
        assert result.output_schema_valid
    """
```

### `tests/test_integration.py`

Three mandatory integration tests — all must pass before any domain bundle is
considered production-ready:

**Test 1 — Basic path:**
`web_search` → `synthesis` → `exec_summary`
Verifies: retrieval → analysis → output works end-to-end with CitationRegistry
populated and citations appearing in the final output.

**Test 2 — Failure path:**
`clinical_search` (forced to return PARTIAL) → `gap_analysis` → replan triggered
Verifies: partial status propagates correctly, gap report is generated, replan
call is made, and new node is added to the plan.

**Test 3 — Sensitivity path:**
`legal_search` → `comparative_analysis` → `report_generator` → disclaimer node
Verifies: sensitivity_flag activates disclaimer node, disclaimer text is present
in final output, jurisdiction_relevance axis is evaluated.

---

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=...

# Optional — tools fall back gracefully if absent
NCBI_EMAIL=your@email.com          # PubMed (free, just needs an email)
GITHUB_TOKEN=...                   # increases GitHub rate limit from 60→5000/hr
TAVILY_API_KEY=...                 # paid web search fallback
GOOGLE_BOOKS_API_KEY=...           # higher rate limit for book search
GOOGLE_TRANSLATE_API_KEY=...       # paid translation fallback
IEEE_API_KEY=...                   # IEEE Xplore search
LIBRETRANSLATE_URL=http://localhost:5000  # self-hosted translation server
```

---

## Build Order Summary

```
Phase 0A: tools/base.py + all 14 tool files
Phase 0B: contracts/SKILL_CONTRACTS.py

Phase 1:  citations/registry.py
          skills/tier1_retrieval/ (18 skills — start with web_search, academic_search)

Phase 2:  skills/tier2_analysis/quality_check.py + prompts/quality_check.md  ← first
          context/budget.py
          skills/tier2_analysis/ (remaining 17 skills + prompts/)

Phase 3:  skills/tier3_output/ (8 skills + prompts/)

Phase 4:  tests/ (all 4 files)
          Run all tests. Fix until all pass.

Final:    Update orchestrator.py to import from new skill modules
          Remove stub classes — replace with real imports
          Run test_integration.py
```

---

## Notes for Claude Code

1. Build phases strictly in order. Do not start Phase 1 skills until
   `SKILL_CONTRACTS.py` is complete and reviewed.

2. Every skill file must import its output schema from `contracts/SKILL_CONTRACTS.py`.
   Do not define schemas inline in skill files.

3. Every retrieval skill must call `ctx.citation_registry.register()` for every
   source before returning. If `ctx.citation_registry` is not yet set in
   `ExecutionContext`, add it to `orchestrator.py` `ExecutionContext` dataclass.

4. The `ContextBudgetManager` must be used by every analysis and output skill
   when building the upstream context string. Never pass raw `ctx.results` directly.

5. All LLM calls in analysis and output skills use `claude-sonnet-4-20250514` as
   a regular model (not reasoning). Max tokens: 2000 for analysis, 4000 for output.

6. All tool calls must use `call_with_retry()` not `call()` directly.

7. When adding a real skill to `orchestrator.py`, remove the `_SimpleStub` for that
   skill from `SKILL_REGISTRY` and replace with the real instance.

8. `SKILL_CONTRACTS.py` schemas are frozen once Phase 1 starts. If a schema change
   is needed, create a migration plan and update all downstream consumers at once.
```