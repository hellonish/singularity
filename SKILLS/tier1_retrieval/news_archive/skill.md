# news_archive

**Tier**: retrieval  
**Name**: `news_archive`  

## Description

This skill is a specialized information retrieval agent that physically queries and fetches recent news articles from a curated list of pre-vetted, authoritative global news outlets. Its primary cognitive process involves executing a targeted web search, filtering results to ensure source credibility and temporal relevance, and then systematically parsing the returned content to extract structured data. The agent performs specific data transformations by taking raw HTML or web content and converting it into a standardized, clean data object. It isolates key article components—headline, author name, publication source, and publication date—from the surrounding webpage noise, normalizing date formats and attributing authorship correctly. The process is designed to be a high-fidelity snapshot of current media discourse from trusted journalistic entities.

## When to Use

- **Specific Scenarios**:
    - When the user query explicitly references a recent event, breaking news story, or ongoing situation (e.g., "What happened with the bank merger today?", "Latest developments in the Middle East peace talks").
    - To gather initial, factual reporting on announcements, press releases, or corporate earnings that have entered the media cycle.
    - To establish a baseline of credible, contemporaneous reporting before deeper analysis (e.g., sentiment tracking, timeline construction).
    - When the task requires understanding the current public narrative or media coverage landscape on a specific topic.
- **Upstream Dependencies & Input Format**:
    - This skill is typically a primary or secondary node in an execution DAG. It expects upstream input to be a well-formed, keyword-rich search query or topic description. The ideal input is a concise string (e.g., "Federal Reserve interest rate decision March 2024") that can be directly used to formulate a web search. It does **not** expect raw, unstructured documents as input.
- **Edge Cases - When NOT to Use**:
    - **For Historical Analysis**: Do not use for events older than roughly one week unless combined with a specific date-range command, as the default filter prioritizes recency.
    - **For Opinion or Commentary**: Avoid using if the need is exclusively for editorials, opinion pieces, or analyst predictions. This tool fetches straight news reporting.
    - **For Highly Niche or Local Topics**: If the topic is unlikely to be covered by major global outlets like Reuters or AP (e.g., very local city council news), this skill may return insufficient data.
    - **As a Substitute for Deep Research**: This is a retrieval skill, not an analysis skill. Do not use it to answer complex "why" or "what does it mean" questions without downstream analytical nodes.
- **Downstream Nodes**:
    - The output of this skill is typically fed into: `summarize` agents for condensation, `sentiment_analyzer` for media tone assessment, `timeline_builder` for event sequencing, or `fact_check` for verification against other sources. It provides the raw, credible news data upon which further processing depends.

## Tools

- WebFetchTool filtered to reuters.com, apnews.com, bbc.com, ft.com, wsj.com

## Execution Model

This skill operates by taking the input query, appending recency-focused search operators (e.g., "past 24 hours" or "past week"), and executing a web search strictly limited to the domains of the authorized outlets. It then fetches the top relevant results, parses each article page to extract the required metadata and snippet of the lead paragraph, and compiles them into the structured output.

## Output Contract

RetrievalOutput — articles with headline, author, publication, date

**Credibility base**: 0.80

**Min sources for OK status**: 3

## Constraints

- **Recency is Mandatory**: You must ALWAYS apply a recency filter to the search (e.g., "last 7 days"). Never perform an open-ended search without a temporal boundary. The default should be the past 24-48 hours for breaking news.
- **Metadata Extraction**: You must diligently extract the `author` and `publication` fields into the output metadata. If an author is not listed, the field should be "Staff" or the publication name, not left blank.
- **Source Limitation**: You are STRICTLY CONFINED to the five listed domains (reuters.com, apnews.com, bbc.com, ft.com, wsj.com). Do not fetch from any other news website, blog, or aggregator, even if they appear in search results.
- **Avoid Hallucination**: Do not infer, guess, or generate any article content. If a key field (like date) cannot be reliably parsed from the page, note it as "Unavailable" in the output rather than inventing it.
- **Token/Volume Management**: Be judicious in the number of articles fetched. Aim for 5-10 of the most relevant articles to provide coverage without overwhelming context windows for downstream nodes. Do not fetch dozens of articles.
- **Status Verification**: The skill must return an "OK" status only if it successfully retrieves articles from at least **three distinct publications** from the allowed list. If you only get results from one or two outlets, the status must be "Partial". This is critical for the credibility score.