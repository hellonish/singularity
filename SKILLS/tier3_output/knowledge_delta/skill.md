# knowledge_delta

**Tier**: output  
**Name**: `knowledge_delta`  

## Description

The `knowledge_delta` skill is a specialized analytical function that performs a rigorous, structured comparison between a newly generated body of knowledge (the "current state") and a previously documented or archived body of knowledge (the "prior state"). Its primary physical action is to ingest two distinct sets of information, apply a systematic cognitive process to analyze their semantic and factual content, and output a precise, categorized summary of the differences. The core cognitive process involves a multi-stage analysis: first, it establishes alignment between entities, topics, and claims across the two states; second, it performs a deep semantic comparison to identify novelty, shifts, and obsolescence; third, it synthesizes these observations into a clean, structured taxonomy of change. The specific data transformation applied is the conversion of two complex, often unstructured or semi-structured, textual knowledge bases into a single, normalized JSON object that explicitly catalogs new developments, changed positions, and deprecated claims, thereby creating a clear, actionable record of intellectual evolution over time.

## When to Use

- **Specific Scenarios**:
    - **Monitoring & Intelligence**: When tracking the evolution of a dynamic subject like a competitive landscape, a fast-moving technology (e.g., AI model releases), geopolitical situation, or clinical trial results over successive time periods.
    - **Recurring Research & Reporting**: For automated weekly, monthly, or quarterly research reports where the goal is to highlight *only what is new or different* since the last report, avoiding redundant information.
    - **Compliance & Audit Trails**: When documenting changes in regulatory frameworks, internal policies, or standards, requiring a clear delta from a known baseline.
    - **Project State Updates**: Comparing the current status, milestones, and risks of a project against its last official review or snapshot.
    - **Knowledge Base Curation**: After a major update to a corpus of documents (e.g., technical manuals, FAQ pages), to generate a summary of what content was added, modified, or removed.

- **Upstream Dependencies**:
    - **Mandatory Input**: This skill REQUIRES two primary inputs:
        1. **Current Findings**: The newly generated, comprehensive output from a preceding research or analysis skill (e.g., `research`, `analyze`, `synthesize`). This is typically a detailed text document or structured data representing the "now" state.
        2. **Prior State Knowledge**: A document or data snapshot representing the "before" state. This is **not** generated on the fly; it must be retrieved. The Planner **must** ensure the plan's metadata contains a `prior_date` key with an ISO 8601 date string (e.g., `"2023-10-26"`). This date is used by the system to locate and retrieve the correct prior state artifact from storage. The skill expects this prior state to be in a comparable format and level of detail to the current findings.
    - **Typical Predecessor Nodes**: This skill is almost always a downstream node of a major synthesis or research agent (e.g., `research_agent`, `synthesize_agent`). Its execution is triggered *after* the current state has been fully assembled.

- **Edge Cases & When NOT to Use**:
    - **No Prior State**: Do **not** invoke this skill if a valid `prior_date` is not available in the plan metadata or if no prior state document exists for that date. It cannot invent a baseline.
    - **First-Time Analysis**: If this is the inaugural analysis on a topic with no historical baseline, this skill is irrelevant. Use a standard `synthesize` or `report` skill instead.
    - **Radically Different Formats/Scopes**: If the current and prior documents cover completely different topics, questions, or formats (e.g., comparing a financial report to a technical spec), the delta will be meaningless and likely erroneous. Ensure scopes are aligned.
    - **Raw, Unprocessed Data**: Do not feed raw, un-synthesized data chunks (like a list of search results or raw transcripts) directly into this skill. It requires coherent, synthesized "knowledge" as input for effective comparison.
    - **Real-Time/Streaming Data**: This skill is designed for periodic, snapshot-based comparison, not for continuous real-time diffing of data streams.

- **Downstream Nodes**:
    - **Report Generation**: The output delta is a perfect input for a `generate_report` or `executive_summary` skill, which can narrativize the changes.
    - **Alerting Systems**: The `new_developments` or `deprecated_claims` sections can trigger notification skills to alert stakeholders.
    - **Knowledge Graph Updates**: The delta can be used to programmatically update a knowledge graph, tagging new entities and retiring old ones.
    - **Dashboard Updates**: The structured output can be directly consumed by a visualization agent to update a monitoring dashboard.

## Execution Model

LLM-based

**Prompt file**: `prompts/knowledge_delta.md`

## Output Contract

OutputDocument — {new_developments, changed_positions, deprecated_claims}

## Constraints

- **Mandatory Metadata**: The plan **must** include `prior_date` in its metadata as an ISO 8601 string (e.g., `"2023-10-26"`). The skill will fail if this key is absent or malformed, as it cannot retrieve the prior state for comparison.
- **Strict Output Schema**: The LLM **must** adhere exactly to the `OutputDocument` schema: a JSON object containing **only** the three specified keys (`new_developments`, `changed_positions`, `deprecated_claims`). Each value should be a well-formatted list or structured text. Do not invent new top-level keys.
- **Explicit Deprecation Marking**: For the `deprecated_claims` field, the LLM **must** explicitly identify claims, facts, or statements that were present and accepted in the prior state but are now contradicted, superseded, or no longer true in the current state. It should not merely list things that are no longer mentioned; there must be positive evidence of obsolescence or correction.
- **Avoid Hallucination of Prior State**: The LLM must rely **solely** on the provided prior state document. It must not hallucinate or assume content for the prior state based on its general knowledge or the content of the current findings.
- **Focus on Semantic Change, Not Minor Wording**: The comparison should focus on substantive changes in facts, conclusions, statuses, and positions. It should ignore trivial rephrasing, grammatical corrections, or formatting changes unless they materially alter meaning.
- **Neutral, Factual Tone**: The output should be a neutral, factual accounting of differences. It should avoid speculative language (e.g., "this might mean...") or editorializing about the quality or implications of the changes.
- **Token Limit Awareness**: The input to this skill (current state + prior state) can be large. The Planner must ensure the combined context does not exceed the model's token window. If documents are extremely large, a preprocessing step to extract key summaries or findings may be necessary upstream.