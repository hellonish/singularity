# credibility_score

**Tier**: analysis  
**Name**: `credibility_score`  

## Description

This skill performs a rigorous, multi-factor credibility assessment on a collection of information sources that have been previously retrieved and stored in the execution context. It is a deterministic analytical function that transforms raw source metadata into a structured, actionable evaluation of source trustworthiness. The skill physically processes the `ctx.credibility_scores` dictionary, which is expected to contain pre-calculated credibility scores (floats between 0.0 and 1.0) keyed by source identifiers (e.g., `slot_1`, `slot_2`). The cognitive process involves: 1) **Aggregation**: Calculating the arithmetic mean of all provided scores to establish a baseline trust level for the entire source set. 2) **Conflict Detection**: Analyzing the distribution and provenance of sources to infer potential bias or coordinated misinformation, flagging any perceived conflict of interest. 3) **Threshold Evaluation**: Comparing the aggregated metrics against predefined confidence thresholds to determine the viability of the source material for downstream tasks. 4) **Recommendation Synthesis**: Generating a prescriptive textual guidance for the Planner and subsequent skills based on the quantitative and qualitative analysis. The final output is a standardized `AnalysisOutput` object containing the computed metrics and guidance.

## When to Use

- **Specific Scenarios**:
    - **Post-Retrieval Analysis**: Immediately after any skill that populates `ctx.credibility_scores` (e.g., `web_search`, `database_lookup`, `document_ingest`).
    - **Pre-Synthesis Gatekeeping**: Mandatory before skills that perform synthesis, summarization, or decision-making (e.g., `synthesize_report`, `answer_formulation`, `risk_assessment`).
    - **High-Stakes Domains**: Essential in all medical/healthcare, legal/judicial, financial/investment, and public policy contexts where source reliability directly impacts outcomes.
    - **Multi-Source Validation**: When information from multiple, potentially conflicting sources (e.g., different news outlets, research papers, financial filings) must be reconciled for trustworthiness.

- **Upstream Dependencies**:
    - **REQUIRED INPUT**: The context must contain a `credibility_scores` dictionary (e.g., `{'slot_1': 0.8, 'slot_2': 0.4}`). This is typically provided by upstream retrieval skills which assign scores based on source authority, freshness, and provenance.
    - **Expected Data Format**: A Python `dict` where keys are source slot identifiers (strings) and values are floating-point numbers in the range [0.0, 1.0]. An empty or missing dictionary will result in a failure.

- **Edge Cases (When NOT to Use)**:
    - **Single, Pre-Vetted Source**: If working with a single, internally generated source or a source whose credibility is axiomatically trusted (e.g., a primary legal statute, a peer-reviewed paper from a top-tier journal already vetted), this skill may be redundant.
    - **Before Any Retrieval**: Do not invoke this skill if `ctx.credibility_scores` is not populated; it is an analysis step, not a retrieval or scoring step.
    - **For Content Analysis**: This skill does *not* analyze the factual content, consistency, or logical soundness of the information itself—only the metadata credibility of its sources. Do not use it to verify factual claims.

- **Downstream Nodes**:
    - **Primary**: `synthesize_report`, `answer_formulation`, `decision_maker`—these skills should consume the `recommendation` and `avg_credibility` to weight their outputs.
    - **Conditional Paths**: The `conflict_of_interest_flag` may trigger a `deep_dive_verification` or `expert_consultation` skill.
    - **Alerting**: A `flag_for_review` or `alert_human` skill may be triggered if the status is `PARTIAL` or `FAILED`.

## Execution Model

Deterministic Python (reads ctx.credibility_scores)

## Output Contract

AnalysisOutput — {avg_credibility, conflict_of_interest_flag, recommendation, scores_by_slot}

## Constraints

- **Threshold Enforcement**: The skill must enforce strict status codes based on the calculated `avg_credibility`. If `avg_credibility < 0.65`, the output status must be `PARTIAL`. If `avg_credibility < 0.50`, the output status must be `FAILED`. The Planner must not override these statuses.
- **Input Validation**: The skill will fail if `ctx.credibility_scores` is missing, empty, not a dictionary, or contains non-numeric values. The Planner must ensure upstream skills provide valid data.
- **No Hallucination of Scores**: This skill is a calculator and flagger. It must **not** generate, estimate, or hallucinate credibility scores. It operates solely on the scores provided in the context. If a source slot is missing a score, it cannot be included in the aggregation.
- **Scope Limitation**: The analysis is limited to the provided scores. It does not fetch new data, re-score sources, or access external databases for additional credibility metrics. The `conflict_of_interest_flag` is a heuristic based on score distribution and source slots (e.g., all low scores from similarly named slots), not on external background checks.
- **Token/Output Limit**: The `recommendation` string must be concise, typically one to two sentences, focusing on the implications of the score for downstream tasks (e.g., "Proceed with caution due to moderate average credibility and a detected potential conflict.").
- **Deterministic Requirement**: Given the same `ctx.credibility_scores` input, the output must be identical. The Planner can rely on this for predictable workflow branching.