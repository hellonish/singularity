# academic_search

**Tier**: retrieval  
**Name**: `academic_search`  

## Description

This skill is a specialized, parallelized academic literature retrieval engine. It physically executes concurrent searches across two major scholarly databases—arXiv (for preprints) and Semantic Scholar (for a broader corpus including published journal articles and conference proceedings). The cognitive process involves: 1) Parsing the user's query into a format suitable for academic search, often focusing on key technical terms, concepts, and named entities. 2) Dispatching semantically identical search requests to both tools simultaneously to minimize latency. 3) Aggregating the raw results, which include metadata like titles, author lists, abstracts, publication years, and source URLs. 4) Applying a deterministic deduplication algorithm that compares the first 50 characters of paper titles; any subsequent entry with a matching title prefix is filtered out to ensure a unique set of papers. 5) Sorting the final, deduplicated list primarily by publication year (most recent first) to satisfy the recency mandate. The core data transformation is from a free-text user query into a structured, chronologically ordered, and unique list of academic paper metadata objects, each tagged with a credibility score based on its publication venue.

## When to Use

- **Specific Scenarios**:
    - When the user's request explicitly asks for "papers," "studies," "research," "literature," or "academic evidence" on a topic.
    - When the query domain is fundamentally scientific, technological, engineering, mathematical, or medical (e.g., "latest transformer architectures," "effects of CRISPR on gene X," "climate models for sea-level rise").
    - When the Planner needs to establish a foundational, citable knowledge base before proceeding to analysis, summarization, or critique tasks.
    - When the task requires distinguishing between cutting-edge preprints (arXiv) and formally published, peer-reviewed work.

- **Upstream Dependencies & Expected Input**:
    - This skill is typically a root or early node in an execution DAG. It expects a well-formed **search query string** as its primary input. This query often comes directly from a user's prompt or is refined by an upstream `query_understanding` or `query_expansion` skill. The input is a plain text string, not structured data.

- **Edge Cases (When NOT to Use)**:
    - **Do NOT use** for searching general web news, commercial products, company information, or non-academic how-to guides.
    - **Avoid** when the user asks for a single, specific, known paper by a complete title and author list; a direct citation lookup tool would be more appropriate.
    - **Ineffective** for highly subjective, opinion-based, or historical (pre-digital era) topics where peer-reviewed literature is sparse.
    - **Not suitable** if the immediate next step requires full PDF text; this skill retrieves metadata and abstracts only.

- **Typical Downstream Nodes**:
    - `summarize`: To create concise overviews of the retrieved papers.
    - `extract_claims`: To identify key findings from the abstracts.
    - `compare_contrast`: To analyze differences between papers.
    - `answer_with_sources`: To ground a Q&A response in the retrieved academic evidence.

## Tools

- ArxivTool
- SemanticScholarTool (both queried in parallel, deduplicated by title)

## Execution Model

The skill executes the ArxivTool and SemanticScholarTool in parallel. It waits for both results, merges them into a single list, applies deduplication based on the first 50 characters of the title, sorts by year (descending), and formats the output according to the `RetrievalOutput` contract.

## Output Contract

RetrievalOutput — papers with title, authors, abstract, year, url

**Credibility base**: 0.88 preprint; 0.95 published journal article

**Min sources for OK status**: 2

## Constraints

- **Recency Filter is Mandatory**: The final output list **MUST** be sorted by publication year in descending order (newest first). Do not present results in any other order.
- **Strict Deduplication**: Deduplicate by comparing the first 50 characters of the `title` field. This is a case-sensitive prefix match. Remove all but the first instance of any duplicate.
- **Source Minimum**: The skill's status is only "OK" if at least **2 unique papers** (post-deduplication) are retrieved across both sources. If only 0 or 1 papers are found, the status should be "ERROR" or similar as per the `RetrievalOutput` contract.
- **No Hallucination of Details**: Only return fields provided by the tools (title, authors, abstract, year, url). Do not infer, generate, or guess missing authors, years, or abstracts.
- **Query Scope Limitation**: The search is constrained to the capabilities of the underlying APIs. Extremely long or complex nested boolean queries may be truncated or may fail. Keep the input query focused and under reasonable length.
- **Credibility Assignment**: Assign the `credibility` score to each paper based on its source: `0.88` for papers sourced primarily from arXiv (preprints), `0.95` for papers from Semantic Scholar that are indicated as published journal/conference articles. If the source is ambiguous, default to the lower (0.88) score.