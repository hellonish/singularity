# patent_search

**Tier**: retrieval  
**Name**: `patent_search`  

## Description

This skill performs a targeted search across specialized patent databases, such as Google Patents (patents.google.com) and Espacenet (espacenet.epo.org), to retrieve comprehensive information on prior art, intellectual property (IP) details, and related technological landscapes. Physically, it operates by sending HTTP requests via the WebFetchTool to these databases, constructing and executing search queries based on provided input parameters, and then parsing the returned HTML or API responses to extract structured data. 

The cognitive process involves several steps: first, it interprets the input query (e.g., keywords, phrases, or specific patent numbers) to formulate a precise search string, applying natural language processing techniques to refine the query for optimal database matching (e.g., handling synonyms, Boolean operators, and date ranges). It then executes the search, which entails navigating the database's search interface programmatically, retrieving a list of relevant patent records, and filtering results based on relevance, such as matching the query's intent for prior art analysis. 

For data transformations, the skill takes unstructured or semi-structured input data—such as a text-based search query string (e.g., "wireless charging technology after 2010")—and transforms it into a structured output. This includes parsing raw web content to extract key elements like patent numbers, assignees, filing dates, and abstracts, then organizing them into a standardized format as defined in the Output Contract. Specifically, it applies data extraction rules (e.g., regular expressions or DOM parsing) to isolate metadata fields, clean and normalize the data (e.g., standardizing date formats, removing duplicates, or truncating overly long abstracts), and ensure the output is query-relevant and non-verbose. This process minimizes errors by cross-verifying results from multiple sources when possible, thereby enhancing accuracy and reducing the risk of incomplete retrievals.

## When to Use

This skill should be employed in specific scenarios where comprehensive patent data retrieval is essential for intellectual property research, such as validating the novelty of an invention, conducting competitive analysis, identifying prior art for patent applications, or mapping technology landscapes in fields like biotechnology, software, or mechanical engineering. For instance, use it when a user needs to check if a concept has been patented previously, such as searching for "autonomous vehicle navigation systems" to support R&D decisions, or when building a report on IP trends in renewable energy.

Upstream dependencies typically require well-formed input data, specifically a clear and concise search query string provided as a text input (e.g., a JSON object containing keywords, date ranges, or patent classifications like IPC codes). The input must be precise to avoid overwhelming the databases; for example, it expects at least one keyword or identifier (e.g., "USPTO patent number 1234567") and may benefit from additional parameters like language filters or geographic restrictions. If the upstream node is a query generator, ensure it outputs structured data (e.g., { "query": "string", "filters": { "date_after": "YYYY-MM-DD" } }) to enable seamless integration.

Edge cases when NOT to use this skill include situations where the query is too vague or broad (e.g., a single word like "invention" without context, which could lead to irrelevant results and exceed query limits), when real-time or highly dynamic data is needed (as patent databases may have delays in updates), or if the task involves non-patent IP like trademarks (which requires a different skill). Avoid using it in scenarios with strict privacy concerns, as it accesses public databases, or when the output volume might overwhelm downstream processes, such as if more than 50 results are expected without pagination. Additionally, do not use it if the Planner has detected unreliable internet connectivity, as it relies on external web access.

Downstream nodes that usually follow this skill include analysis tools (e.g., a summarization agent to condense abstracts), data aggregation skills (e.g., combining results with market data), or decision-making modules (e.g., evaluating patent validity). For example, after retrieving patents, a typical flow might involve a "patent_analysis" skill to assess infringement risks or a "report_generator" to compile findings into a document.

## Tools

- WebFetchTool filtered to patents.google.com, espacenet.epo.org

## Output Contract

RetrievalOutput — patents with patent_number, assignee, filing_date, abstract

**Credibility base**: 0.95

**Min sources for OK status**: 2

## Constraints

This skill operates under strict limitations to ensure reliable and ethical use. First, it must adhere to token or query limits imposed by the underlying databases, such as restricting search queries to a maximum of 200 characters to prevent truncation or errors, and limiting the number of requests per minute (e.g., no more than 5 queries in a 60-second window) to comply with API rate limits and avoid bans. 

To prevent hallucinations, the skill is designed to only return data directly extracted from verified sources (patents.google.com and espacenet.epo.org), with no generative content added—always cross-reference at least two sources for key facts as per the Output Contract's minimum sources requirement. It must not extrapolate or infer beyond the retrieved data, such as avoiding assumptions about patent ownership or future implications.

Additionally, confine its scope strictly to patent-related queries; do not use it for general web searches or unrelated domains, as this could lead to inaccurate results or scope creep. Ensure all extracted metadata (e.g., patent_number and assignee) is accurately placed into the output's metadata field without alteration, and handle potential errors gracefully, such as returning an error code if no results are found or if the query format is invalid. Finally, the skill requires a stable internet connection and should only be invoked in environments with access to these specific tools, avoiding any offline or simulated data to maintain credibility.