# sentiment_cluster

**Tier**: analysis  
**Name**: `sentiment_cluster`  

## Description

The `sentiment_cluster` skill performs a sophisticated, multi-dimensional analysis on a collection of social media posts or forum comments to map the opinion landscape. It does not merely categorize by positive/negative/neutral sentiment. Instead, it executes a cognitive process that first deeply comprehends the semantic content, emotional tone, and implied stance within each text unit. It then identifies latent thematic patterns and affective alignments across the dataset. The core data transformation involves applying an LLM to simultaneously evaluate sentiment (including nuanced emotions like skepticism, enthusiasm, or frustration) and extract dominant topics or concerns. These dual vectors—sentiment and topic—are then used to group posts into coherent clusters where members share both a common thematic focus and a similar emotional valence. The skill synthesizes each cluster by generating a descriptive label that captures the topic-sentiment fusion, calculating the cluster's proportional size, and selecting a small set of representative posts that best exemplify the cluster's core attributes. The final output is a structured, high-level taxonomy of the discourse, revealing not just what is being discussed, but *how* it is being felt and argued by the community.

## When to Use

- **Specific Scenarios**:
    1.  **Post-Search Analysis**: Immediately after executing `social_search` or `forum_search` to transform raw result lists into an intelligible map of public opinion.
    2.  **Competitive or Brand Monitoring**: To dissect the conversation around a product launch, corporate announcement, or PR crisis into distinct supporter, critic, and neutral observer cohorts, each with their specific grievances or praises.
    3.  **Policy or Idea Testing**: To understand the fractured reception of a new proposal, feature, or policy change, identifying clusters based on specific concerns (e.g., "privacy worries - negative" vs. "usability praise - positive").
    4.  **Community Dynamics Mapping**: To analyze forum threads to identify sub-communities or ideological factions based on their prevailing sentiment and topical focus.

- **Upstream Dependencies & Input Format**:
    - **Primary Upstream Skill**: `social_search` or `forum_search`. This skill is designed to consume the `SearchOutput` from those skills.
    - **Required Input Data Format**: It expects a list of social posts or forum comments, where each item should ideally contain `content` (the primary text) and `source` metadata. The LLM prompt is engineered to process this list-of-dicts structure. Raw, unparsed HTML or JSON blobs will cause failure.

- **Edge Cases - When NOT to Use**:
    1.  **On Very Small Datasets**: If the upstream search returns fewer than ~10-15 unique posts, clustering will be meaningless or overly granular. Consider using `summarize` or `sentiment_analysis` instead.
    2.  **On Non-Opinion Data**: Do not use for clustering factual news articles, technical documentation, or code. It is optimized for subjective, user-generated content.
    3.  **As a Replacement for Quantitative Metrics**: This skill provides qualitative, interpretive clusters. It does not output precise sentiment scores, volume trends, or network graphs. For those, pair it with other analytical skills.
    4.  **Before Data is Gathered**: This is an analysis skill, not a fetch skill. It requires the post data to already be in the execution context.

- **Typical Downstream Nodes**:
    1.  `report_summarize`: To create an executive summary of the key clusters identified.
    2.  `trend_analysis`: To compare clusters against temporal data or track cluster evolution over time.
    3.  `recommendation_engine`: To generate actionable insights (e.g., "address the concerns in cluster X") based on the cluster analysis.
    4.  `visualization`: To produce charts or graphs depicting the cluster landscape (though the skill itself does not generate visuals).

## Constraints

1.  **Input Token Limit**: The skill passes the collected posts to an LLM. The Planner **MUST** ensure the total concatenated text from all posts does not exceed the context window of the execution LLM (e.g., 128K tokens). For very large result sets, the Planner should first use a `filter` or `summarize` skill to reduce the volume before clustering.
2.  **No Hallucination of Data**: The LLM must only cluster based on the posts provided in the input. It must not invent posts, sentiments, or topics not present in the source data. The prompt is designed to enforce this, but the Planner should be aware.
3.  **Scope Limitation**: This skill analyzes the *textual content* of posts. It does **not**:
    -   Perform network analysis (who replied to whom).
    -   Analyze images, videos, or linked articles.
    -   Fetch additional data from the web or APIs.
    -   Attribute posts to specific real-world individuals beyond what's in the provided source field.
4.  **Non-Deterministic Outputs**: Clustering is an interpretive act. Slight variations in input or model temperature may produce different cluster labels and boundaries. The skill is designed for insightful approximation, not perfectly reproducible taxonomies.
5.  **Representative Post Selection**: The "representative_posts" are chosen by the LLM for exemplarity, not by an external metric like most likes/retweets. The Planner should not assume they are the most popular posts, merely the most characteristic.

## Execution Model

LLM-based

**Prompt file**: `prompts/sentiment_cluster.md`

## Output Contract

AnalysisOutput — clusters: [{label, sentiment, representative_posts, size}]