# social_search

**Tier**: retrieval  
**Name**: `social_search`  

## Description

This skill performs targeted retrieval of public, user-generated content from major social media platforms to capture real-time sentiment and public opinion signals. It physically executes a web search via the WebFetchTool, applying strict filters to limit results to recognized social media domains (e.g., twitter.com, reddit.com, facebook.com, linkedin.com, instagram.com, tiktok.com). The cognitive process involves parsing search results to identify individual posts or threads, then analyzing the textual content to classify the prevailing sentiment expressed within each post. The core data transformation is the conversion of raw, unstructured social media text into a structured dataset where each entry includes the post's content, source platform, publication timestamp (if available), and an assigned sentiment label (`positive`, `negative`, or `mixed`). This process aggregates disparate social signals into a quantifiable overview of public perception on a given topic, brand, or event.

## When to Use

- **Specific Scenarios**:
    - **Brand Health Monitoring**: Assessing public reaction to a new product launch, marketing campaign, or corporate announcement.
    - **Crisis Management & PR**: Gauging the scale and sentiment of public discourse during a corporate controversy or public relations incident.
    - **Trend Detection & Validation**: Identifying emerging topics, hashtags, or memes and understanding the associated public sentiment.
    - **Competitive Intelligence**: Comparing public sentiment toward a client's brand versus key competitors.
    - **Market Sentiment Analysis**: Understanding retail investor or consumer sentiment toward a company, stock, or cryptocurrency.
    - **Event Impact Analysis**: Measuring public reaction to live events, earnings calls, or political debates.

- **Upstream Dependencies**:
    - This skill typically requires a clear, concise search query or topic string as input. The query should be specific enough to yield relevant social posts (e.g., "Apple Vision Pro user reviews" is better than just "Apple"). It may follow a `generate_queries` skill that formulates optimal search strings for social platforms.

- **When NOT to Use (Edge Cases)**:
    - **For Factual Verification**: Never use this skill to establish objective truths, statistics, or event details. Social media is opinion, not evidence.
    - **For In-Depth Technical Analysis**: Do not use it to gather detailed technical specifications, financial data, or scientific findings.
    - **When Seeking Official Sources**: If the task requires press releases, government reports, or corporate filings, use `news_search` or `academic_search` instead.
    - **For Private or Historical Data**: This skill retrieves publicly accessible, recent posts. It cannot access private accounts or perform deep historical archival searches.
    - **As a Standalone Source**: This skill's output must always be contextualized and combined with higher-credibility sources.

- **Downstream Nodes**:
    - The structured sentiment data is typically passed to a `synthesize` or `analyze` skill (e.g., `sentiment_analysis`, `trend_synthesis`) to identify overarching themes, sentiment trends over time, or to be integrated into a broader report alongside news and financial data.

## Tools

- WebFetchTool filtered to social platforms

## Execution Model

This skill is executed as a retrieval node. It takes a search query, performs the fetch, processes the results to extract posts and assign sentiment, and returns a structured `RetrievalOutput`.

## Output Contract

RetrievalOutput — posts with sentiment (mixed/positive/negative), platform

**Credibility base**: 0.60

**Min sources for OK status**: 5

## Constraints

- **Inherently Low Credibility**: Social media content is user-generated, unverified, and often biased. The base credibility score of 0.60 must be prominently considered by the Planner. The output **must always explicitly disclose** that the source type is "social media" or "public forum."
- **Not for Factual Claims**: This skill's output **must never** be used as the sole or primary evidence for any factual claim. It is strictly for measuring opinion and sentiment.
- **Volume Requirement**: To achieve an "OK" status, the skill must successfully retrieve and process a minimum of 5 distinct social media posts/sources. Fewer than 5 indicates insufficient data for reliable signal detection.
- **Sentiment Labeling Scope**: Sentiment analysis is performed at the post level. It does not perform nuanced aspect-based sentiment (e.g., "positive about battery life but negative about price") unless explicitly coded in future iterations. The current labels are generalized.
- **Temporal Recency Bias**: The search is optimized for recent posts. It may not capture long-term sentiment shifts unless specifically queried for historical trends, which is not its primary function.
- **Platform Limitations**: Results are constrained to platforms the WebFetchTool can access and filter for. Some platforms with restrictive APIs or non-text-heavy content (e.g., TikTok, Instagram) may be underrepresented in textual analysis.
- **Advisory Nature**: All conclusions drawn from this skill's output should be framed as "public perception indicates..." or "social sentiment suggests...", not as statements of fact.