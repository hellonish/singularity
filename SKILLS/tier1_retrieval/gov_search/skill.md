# gov_search

**Tier**: retrieval  
**Name**: `gov_search`  

## Description

The gov_search skill is a specialized information retrieval agent that performs targeted web searches with a strict domain restriction to official United States government digital properties. It physically executes a programmatic search query via a configured WebFetchTool, which interfaces with the DuckDuckGo search engine, appending the `site:*.gov` filter to every query. This ensures all returned results originate from top-level domains (TLDs) ending in `.gov` (e.g., `.gov`, `.gov.uk`, `.gov.au`) or second-level domains under `.gov` (e.g., `agency.gov`). The agent's cognitive process involves parsing the user's information need, formulating a concise and effective search query string that maximizes relevance within the government domain constraint, and executing the search. It then processes the raw search results, performing a data transformation by extracting, validating, and structuring the retrieved content into a standardized `RetrievalOutput` format. This includes parsing each source for identifiable government departments or agencies and attempting to infer or locate publication dates to enhance the metadata's utility for downstream fact-checking and synthesis tasks. The agent's core function is to act as a high-credibility funnel, pulling raw official data, reports, regulations, guidance documents, and statistical publications directly from primary government sources.

## When to Use

Use this skill as the primary retrieval node in scenarios demanding high-authority, official information from public sector entities. Specific scenarios include:
*   **Policy & Legislative Research**: Searching for the text of enacted laws, proposed bills (e.g., from congress.gov), white papers, or official policy statements from executive departments.
*   **Regulatory Compliance & Rulemaking**: Retrieving current Code of Federal Regulations (CFR) sections, Federal Register notices, regulatory impact analyses, or guidance documents from agencies like the EPA, FDA, or SEC.
*   **Official Statistics & Economic Data**: Gathering datasets, reports, and indicators from statistical agencies (e.g., Bureau of Labor Statistics (bls.gov), Census Bureau (census.gov), Bureau of Economic Analysis (bea.gov)).
*   **Public Health & Safety Guidance**: Finding latest advisories, disease control protocols, vaccine information, or safety standards from bodies like the CDC (cdc.gov), FDA (fda.gov), or NIH (nih.gov).
*   **Administrative & Procedural Information**: Locating official forms, application processes, eligibility criteria, or contact information for government services.

**Upstream Dependencies & Input Format**: This skill typically follows a planning or query-formulation node. It expects a clear, focused search query string as its primary input. The query should be keyword-rich and tailored to find documents within government sites (e.g., "BLS unemployment rate March 2024" or "FDA guidance clinical trials digital health tools"). It does **not** accept raw, unfiltered user questions; those must be pre-processed into an effective search string.

**Edge Cases - When NOT to Use**:
*   **Non-Governmental or International Sources**: Do not use for retrieving information from academic journals (.edu), commercial news outlets (.com), international organizations (UN, WHO - typically .org), or non-governmental think tanks.
*   **Highly Technical or Niche Scientific Research**: While NIH and other .gov sites host scientific content, for cutting-edge, pre-print, or highly specialized research not yet adopted into official guidance, a broader academic search may be more appropriate first.
*   **Local/Municipal Government Info**: Many city and county governments use `.org`, `.us`, or other TLDs. This skill's `*.gov` filter will miss them. Do not use for hyper-local information unless you confirm the domain.
*   **Opinion or Commentary**: Avoid using it to find editorial content or opinion pieces, even if hosted on .gov sites (e.g., blog posts). The skill is designed for official publications.
*   **Real-Time/Breaking News**: Government websites are not optimized for minute-by-minute news. For breaking events, a general news search is better, though official statements can be retrieved later via this skill.

**Downstream Nodes**: The retrieved `RetrievalOutput` is typically fed into:
1.  **Analysis/Synthesis Skills**: Such as `summarize`, `synthesize`, or `fact_check` agents that need credible source material.
2.  **Answer Formulation Nodes**: That incorporate the retrieved evidence into a final, sourced answer.
3.  **Secondary Retrieval Skills**: If initial results are insufficient, a planner might chain this with a `web_search` (broader search) or a `site_specific_search` (deep dive on a specific .gov domain found here).

## Tools

- WebFetchTool with site:*.gov DuckDuckGo filter

## Output Contract

RetrievalOutput — sources with department, publication_date

**Credibility base**: 0.95

**Min sources for OK status**: 2

## Constraints

1.  **Strict Domain Filtering**: The `site:*.gov` filter is MANDATORY and NON-NEGOTIABLE. The agent must NEVER modify, remove, or bypass this filter. All search queries must be constructed to work effectively within this constraint.
2.  **Source Quality & Quantity**: The agent must strive to retrieve at least the **minimum of 2 distinct sources** from different government domains or subdomains to achieve an "OK" status. Relying on a single source is insufficient unless explicitly overridden by the planner due to task nature.
3.  **Avoid Hallucination of Metadata**: If the department/agency or publication date cannot be reliably determined from the source page's content or standard metadata (e.g., visible headers, "Last updated" footers), the agent must label them as `null` or with a best-effort placeholder (e.g., "U.S. Federal Agency") rather than inventing plausible details. Accuracy of metadata is secondary to accuracy of the source content itself.
4.  **Query Formulation Limits**: The agent must craft search queries that are specific enough to be relevant but within the practical limits of web search. Avoid excessively long queries (e.g., full sentences). Prioritize key nouns, acronyms, and dates.
5.  **No Content Generation or Synthesis**: This is a pure retrieval skill. The agent must NOT interpret, summarize, or combine information from the fetched sources within this node's execution. Its output is strictly the collected source texts and their metadata.
6.  **Credibility Assumption**: While the .gov domain provides a high credibility base (0.95), the agent should remain aware that not all content on a .gov site carries equal weight (e.g., a press release vs. a peer-reviewed NIH study). It should prioritize retrieving primary documents (laws, reports, datasets) over secondary content (news updates, blog posts) when possible, as inferred from the search results.