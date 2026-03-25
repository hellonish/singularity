# trend_analysis

**Tier**: analysis  
**Name**: `trend_analysis`  

## Description

This skill performs a rigorous, multi-step analytical process to identify, characterize, and substantiate directional trends within sequential or time-series data. It is not a simple pattern detector but a structured reasoning engine that transforms raw temporal data into actionable trend intelligence.

**Physical & Cognitive Process:**
1.  **Data Ingestion & Temporal Validation:** First, the skill ingests the provided context, which must contain dated information (e.g., reports with timestamps, time-series data points, chronological event logs). It immediately validates the presence and consistency of temporal markers.
2.  **Dimension Isolation:** It then parses the data to isolate distinct `dimensions` or variables of interest (e.g., "stock price of Company X," "global average temperature," "mentions of AI in news articles," "monthly active users").
3.  **Temporal Sequencing & Point Mapping:** For each isolated dimension, it chronologically orders all relevant data points, creating a clean time series.
4.  **Directional Inference:** Using statistical reasoning (e.g., assessing slope, comparing start vs. end values, identifying inflection points) and qualitative assessment, it determines the primary `direction` of change over the observed period. Directions are categorized as: `increasing`, `decreasing`, `stable` (no significant change), `volatile` (no clear directional consensus), or `cyclical` (predictable repeating pattern).
5.  **Evidence Curation:** For each identified trend, the skill extracts the most salient, date-anchored data points that concretely support the directional claim (e.g., "Q1 2023: $100; Q4 2023: $150").
6.  **Confidence Calibration:** It assigns a `confidence` score (High, Medium, Low) based on the quality, quantity, and consistency of the dated evidence, as well as the clarity of the trend signal versus noise.

**Data Transformation:** The skill transforms unstructured or semi-structured chronological text/data into a structured JSON-like list of trend objects, each containing the four key properties defined in the Output Contract.

## When to Use

Use this skill when the core task requires understanding *how something has changed over time* and you need a structured, evidence-based summary of those changes.

**Specific Scenarios:**
*   **Market/Financial Analysis:** Analyzing stock price movements, revenue growth, market share evolution, or commodity price fluctuations over quarters/years.
*   **Technology Adoption:** Tracking the rise or decline in usage metrics (downloads, active users), search interest, or funding for a specific technology.
*   **Epidemiological/Public Health:** Identifying the progression of disease case counts, vaccination rates, or public sentiment during a health crisis.
*   **Social/Sentiment Analysis:** Observing shifts in public opinion, media tone, or brand sentiment across a news cycle or campaign period.
*   **Operational Metrics:** Reviewing changes in website traffic, customer support ticket volume, or manufacturing output over time.
*   **Academic/Research:** Summarizing the historical development of citations for a theory or the publication volume in a research field.

**Upstream Dependencies & Expected Input:**
*   **Primary Input:** A body of text or structured data **where dates are explicitly tied to facts or metrics**. This could be the output from a `search` skill filtered for recent articles, a `data_query` result with timestamps, or a compiled chronology from `information_synthesis`.
*   **Required Format:** The input must allow the LLM to clearly associate a value/state (e.g., "revenue was $1M") with a specific point in time (e.g., "in 2022"). Vague references like "recently" or "over the past few years" without concrete anchors are insufficient.

**Edge Cases - When NOT to Use:**
*   **Atemporal Data:** If the provided sources or context contain **no dates or timestamps**, this skill must be declined. Use `information_synthesis` or `summarization` instead.
*   **Predictive Forecasting:** This skill analyzes *past* trends. Do not use it to *predict future* states. For forecasting, a dedicated `forecasting` or `scenario_planning` skill is required.
*   **Single Point-in-Time Analysis:** If the task is to understand a *current state* or snapshot, not a change, use `summarization` or `current_state_analysis`.
*   **Causal Analysis:** This skill identifies *what* trend occurred, not *why*. To determine causes or correlations, chain its output to a `causal_analysis` or `root_cause_analysis` skill.

**Typical Downstream Nodes:**
*   `report_generation` or `executive_summary` to present the trend findings.
*   `causal_analysis` to investigate drivers behind the identified trends.
*   `implication_analysis` or `risk_assessment` to explore the consequences of the trends.
*   `forecasting` (if sufficient historical data exists) to project the trend forward.
*   `recommendation_engine` to suggest actions based on the trend direction.

## Execution Model

LLM-based

**Prompt file**: `prompts/trend_analysis.md`

## Output Contract

AnalysisOutput — trends: [{dimension, direction, evidence, confidence}]

## Constraints

- **Mandatory Temporal Data:** This skill **must decline execution** if the provided context lacks clear, explicit dates or timestamps associated with the data points to be analyzed. Do not hallucinate or infer dates.
- **Strict Output Schema:** Adhere precisely to the `AnalysisOutput` contract. Each `trend` object must contain exactly the four fields: `dimension` (string), `direction` (string from the defined set), `evidence` (string with concrete, dated points), and `confidence` (string: High/Medium/Low).
- **Evidence-Based Rigor:** Every declared trend **must** be backed by specific evidence cited directly from the source material. Avoid speculative trends or those based on a single, outlier data point.
- **Scope Limitation:** Analyze only trends present in the **provided source context**. Do not incorporate general knowledge or trends not explicitly supported by the ingested data. The analysis is bounded by the input.
- **Dimension Focus:** Identify trends for clear, measurable dimensions. Avoid overly vague or subjective dimensions (e.g., "happiness" without a proxy metric). Prefer concrete metrics, counts, frequencies, or clearly defined states.
- **Token Management:** When processing very long time-series data, focus on summarizing the overarching trend and key evidential points rather than listing every single data point. The `evidence` field should be a concise summary, not a full data dump.