# timeline_construct

**Tier**: analysis  
**Name**: `timeline_construct`  

## Description

This skill performs a detailed, multi-step cognitive process to synthesize a structured, chronological timeline from disparate upstream information sources. It physically ingests raw data—typically in the form of text documents, extracted facts, or summarized reports—and applies a rigorous analytical transformation. The agent first parses the input to identify discrete events, actions, or state changes. It then performs temporal reasoning to isolate, extract, and normalize date or time references associated with each event, converting relative terms (e.g., "last quarter," "two years prior") into absolute or standardized date formats where possible. Each event is then contextualized and distilled into a clear, concise description. Crucially, the skill traces every piece of information back to its originating source material, creating an explicit citation link. Finally, it sequences all identified events into a single, ordered list based on their temporal logic, from earliest to latest, producing a coherent narrative of progression over time. The output is not a simple list but a validated data structure where each entry is anchored to evidence and its temporal placement is justified.

## When to Use

- **Specific Scenarios**:
    - **Historical Analysis**: Reconstructing the sequence of key decisions, battles, or discoveries in a historical period.
    - **Incident Investigation**: Building a minute-by-minute or day-by-day account of a security breach, accident, or system failure from logs and reports.
    - **Policy or Law Evolution**: Charting the introduction, amendment, and repeal of legislation, regulations, or corporate policies.
    - **Biographical Sequencing**: Creating a chronicle of significant life events, career milestones, or publications of an individual or organization.
    - **Project/Process Tracking**: Ordering the major phases, deliverables, and decision points in a development lifecycle or business process.
    - **Narrative Clarification**: Resolving confusion in a complex story by establishing the definitive order of events from conflicting accounts.

- **Upstream Dependencies & Expected Input**:
    - This skill **requires** processed textual data as input. It typically follows skills like `document_loader`, `text_summarizer`, `fact_extractor`, or `source_consolidator`.
    - The input format is usually a string or list of strings containing the relevant facts, summaries, or document chunks. The input **must contain** explicit or inferable temporal references and event descriptions. Raw, unstructured binary data (like images or audio) is not suitable unless previously processed into text.

- **Edge Cases - When NOT to Use**:
    - **Purely Predictive Tasks**: Do not use for forecasting future events or creating speculative timelines.
    - **Data Without Time Context**: If the source material contains no dates, times, or sequence indicators (e.g., "first," "then," "after"), this skill will fail or produce an empty output.
    - **Scheduling or Calendar Creation**: This is for historical reconstruction, not for planning future meetings or creating project schedules (use a planning skill instead).
    - **Single-Source, Already-Chronological Narratives**: If the input is a single document already written in perfect chronological order (like a timeline report), this skill is redundant; use a `summarizer` or `paraphraser`.

- **Downstream Nodes**:
    - The structured timeline output is commonly fed into:
        - `report_generator` or `narrative_writer` to produce a prose summary of the sequence.
        - `gap_analyzer` to identify missing periods or information.
        - `causal_analysis` to investigate relationships between sequential events.
        - `visualization_generator` to create Gantt charts or time-series diagrams.

## Execution Model

LLM-based

**Prompt file**: `prompts/timeline_construct.md`

## Output Contract

AnalysisOutput — events: [{date, event, source_citation, confidence}]

## Constraints

- **Source Citation Mandate**: Every single event entry in the timeline **MUST** include a `source_citation`. This citation must directly point to the excerpt or data point in the upstream source material that provided the evidence for the event. **Hallucination of events without a verifiable source is strictly prohibited.** If an event cannot be cited, it must be omitted.
- **Temporal Uncertainty Handling**: Dates that are approximate, inferred, or partially unknown **MUST** be flagged by prefixing the `date` field with a tilde (`~`), e.g., "~June 2023" or "~Q4 1999". Do not use this for fully known dates.
- **Scope Limitation**: The timeline must be constructed **SOLELY** from the information provided in the immediate upstream input. Do not incorporate general knowledge, external facts, or personal assumptions not present in the source texts. The LLM must act as a strict synthesizer of the given data.
- **Output Format Fidelity**: Adhere exactly to the `AnalysisOutput` schema. The `events` list must be an array of objects with the specified keys (`date`, `event`, `source_citation`, `confidence`). Do not add extra keys or alter the structure.
- **Confidence Scoring**: The `confidence` field must reflect a reasoned judgment (e.g., "High", "Medium", "Low") based on the clarity of the source and the specificity of the date. Low confidence should be used for events inferred from ambiguous language.
- **Token & Detail Management**: Be concise in the `event` description. Capture the core action or change, avoiding lengthy narrative. The primary goal is accurate sequencing, not exhaustive detail.