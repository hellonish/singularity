# web_search

**Tier**: retrieval
**Name**: `web_search`

## Description

The `web_search` skill is a robust, general-purpose information retrieval mechanism designed to query and fetch publicly accessible web content that directly addresses a given user query. Physically, it operates by interfacing with external search APIs—primarily DuckDuckGo for its privacy-focused, unbiased results, with Tavily as a reliable fallback in case of API rate limits, downtime, or suboptimal result quality—to generate a targeted search query string derived from the input. This query string is then submitted to the search engine, which returns a ranked list of web page results including URLs, titles, and textual snippets. The skill processes these raw results by extracting and curating the most relevant snippets (typically 100-300 words per source) that contain key factual or contextual information pertinent to the query, while discarding irrelevant or low-quality hits such as advertisements, paywalled content, or non-textual media.

Cognitively, the skill employs a multi-step reasoning process: (1) Query refinement—analyzing the input query for clarity, specificity, and potential ambiguities to rephrase it into an optimized search string (e.g., adding Boolean operators like "AND" or quotes for exact phrases if needed); (2) Relevance scoring—internally evaluating returned results against the query using semantic similarity metrics (e.g., keyword overlap, topical alignment) to select the top N results (default N=10, adjustable based on query complexity); (3) Credibility assessment—assigning a base credibility score to each source based on domain type (0.75 for general .com/.org sites, elevated to 0.85 for authoritative .gov or .edu domains) and additional heuristics like publication date, source reputation (e.g., avoiding known misinformation sites), and snippet coherence; (4) Data sanitization—filtering out duplicate content, removing HTML artifacts, and ensuring snippets are concise yet informative. This process transforms unstructured web data into a structured, query-aligned knowledge base, enabling downstream agents to synthesize accurate, evidence-based responses without hallucination risks.

The skill applies specific data transformations: Input (a natural language query string, optionally with parameters like 'recency' or 'num_results') → Raw search API response (JSON with URLs, titles, snippets) → Curated output (RetrievalOutput object containing a list of sources, each with URL, extracted snippet, and credibility_base score). Transformations emphasize factual extraction, preserving original wording where possible to maintain verifiability, and include metadata like fetch timestamp for traceability. Overall, this skill acts as a foundational retrieval layer, bridging the gap between vague user intents and concrete, external knowledge sources in a retrieval-augmented generation (RAG) pipeline.

## When to Use

Deploy the `web_search` skill in scenarios requiring broad, real-time access to diverse, publicly available online information where specialized internal databases (e.g., proprietary knowledge bases or domain-specific APIs) are unavailable or insufficient. Specific use cases include: (1) General fact-finding, such as verifying current events, historical details, or scientific concepts not covered in local caches (e.g., "What are the latest advancements in quantum computing?"); (2) Exploratory research for topics spanning multiple domains, like market trends, cultural insights, or technical tutorials (e.g., "Best practices for sustainable agriculture in arid regions"); (3) Fallback augmentation when primary retrieval skills (e.g., vector search over documents) yield incomplete or zero results, ensuring comprehensive coverage; (4) Hypothesis validation in reasoning chains, where external corroboration is needed to ground speculative outputs.

Upstream dependencies typically include a well-formed input query from a Planner or Query Refiner node, expecting a string format like "query: [natural language question]" with optional JSON parameters (e.g., {"recency": "past_year", "num_results": 5}). The input should be concise (under 100 tokens) and unambiguous to avoid diluted results; if the query is vague, prepend a refinement step. Avoid using if upstream provides already-structured data (e.g., from a database query) to prevent redundant API calls.

Edge cases when NOT to use: (1) Queries involving sensitive, private, or non-public data (e.g., personal records, internal company info)—redirect to authenticated tools instead; (2) Highly specialized or niche technical domains better served by APIs like PubMed or arXiv (e.g., medical diagnoses); (3) Real-time or ultra-low-latency needs (e.g., live stock prices)—opt for dedicated financial APIs; (4) When the query explicitly requests opinion-based or creative content without factual grounding, as this skill prioritizes verifiable sources; (5) In low-resource environments with strict API quotas, as it consumes external credits.

Downstream nodes usually following this skill include: (1) Summarizer or Synthesizer agents to aggregate and distill snippets into coherent narratives; (2) Fact-Checker to cross-verify credibility scores against additional sources; (3) Response Generator for integrating retrieved data into user-facing outputs; (4) Cacher to store results for reuse in iterative queries, reducing repeated calls.

## Tools

- WebFetchTool (DuckDuckGo primary, Tavily fallback)

## Output Contract

RetrievalOutput — sources list with url, snippet, credibility_base

**Credibility base**: 0.75 general web; 0.85 for .gov/.edu domains

**Min sources for OK status**: 3

## Constraints

Adhere strictly to these limitations to ensure reliable, ethical, and efficient operation: (1) No jurisdiction or geographic filtering—results are global and unlocalized, potentially including region-specific biases; always disclose this in downstream outputs if relevance to user location matters; (2) Token limits—curate snippets to under 512 tokens per source and limit total output to 10 sources max to avoid overwhelming Planner context windows (e.g., GPT-4's 8k-128k limits); truncate longer content with "[...]" indicators; (3) Avoid hallucinations—stick exclusively to fetched snippets without injecting external knowledge or assumptions; if results are insufficient (<3 sources), flag as "partial" status and suggest query refinement; (4) No external scope expansion—do not follow links, scrape full pages, or access paywalled/JavaScript-heavy sites; rely solely on search engine snippets for surface-level retrieval; (5) Recency enforcement—if 'recency' is specified in input axes (e.g., "past_month"), apply temporal filters via API parameters (DuckDuckGo's built-in sorting or Tavily's date_range), prioritizing sources within the window and deprioritizing older ones; default to no filter for timeless queries; (6) Rate limiting and ethics—respect API quotas (e.g., 10 queries/minute for DuckDuckGo), avoid sensitive topics (e.g., illegal activities), and ensure all fetches comply with robots.txt and public access norms; (7) Error handling—on API failure, fallback to secondary tool within 2 retries, then return empty sources with error metadata rather than fabricating data.