# entity_extraction

**Tier**: analysis  
**Name**: `entity_extraction`  

## Description

This skill performs a detailed, structured Named Entity Recognition (NER) analysis on a provided text corpus. It physically processes the input text by scanning it token-by-token, applying a sophisticated cognitive process that involves pattern recognition, contextual disambiguation, and semantic classification. The core data transformation is the conversion of unstructured natural language text into a structured, deduplicated list of identified entities, each annotated with its type, specific mentions, and surrounding context.

The cognitive process involves: 1) **Segmentation**: Parsing the text into sentences and phrases to establish boundaries. 2) **Candidate Identification**: Locating spans of text that represent potential named entities based on capitalization, adjacent words, and linguistic patterns. 3) **Classification & Typing**: Assigning each candidate to a predefined category (Person, Organization, Location, Date, etc.) by analyzing its morphological features, syntactic role, and the semantic context in which it appears. 4) **Coreference Resolution**: Linking different textual mentions (e.g., "Dr. Smith", "he", "the doctor") to a single, canonical entity representation to avoid duplication. 5) **Context Extraction**: Capturing the immediate sentence or clause containing each mention to preserve the entity's narrative role. 6) **Structuring**: Aggregating all data into the strict `AnalysisOutput` format required by the Output Contract.

## When to Use

Use this skill in the following specific scenarios:
*   **Downstream Structured Analysis**: When subsequent nodes in the DAG require clean, categorized entity data for tasks like relationship mapping (e.g., `relationship_mapping`), knowledge graph population, summarization focused on key actors, or sentiment analysis per organization.
*   **Information Triage & Filtering**: To extract key actors (People, Organizations) and locations from large documents (e.g., news articles, legal briefs, corporate reports) to enable focused research or content filtering.
*   **Data Enrichment Pipelines**: As a critical preprocessing step before skills that perform lookups or fetch additional data about specific entities (e.g., fetching a company profile requires first cleanly identifying the company name from text).
*   **Compliance & Monitoring**: To scan communications or documents for mentions of specific regulated entities, individuals, or geopolitical locations.

**Upstream Dependencies & Input Format**:
*   This skill **requires** upstream text data. The primary input is typically the `text` field from a `TextAnalysisNode` or similar node that has aggregated or produced a coherent text corpus (e.g., from `web_search`, `document_parsing`, or `text_summarization`).
*   The input text should be as clean as possible. While the skill can handle some noise, upstream skills like `text_cleanup` or `chunking` (for very long documents) can significantly improve accuracy.

**Edge Cases - When NOT to Use**:
*   **For Simple Keyword Matching**: Do not use if the goal is merely to find the presence of a pre-defined list of terms; use a `text_filtering` or `pattern_matching` skill instead.
*   **On Non-Textual or Binary Data**: This skill cannot process images, audio, raw PDFs, or structured data (JSON, CSV) directly. Ensure upstream parsing has occurred.
*   **For Fine-Grained Entity Typing Beyond Standard Categories**: If the requirement is to identify highly specialized entity types (e.g., "medical procedure," "legal statute"), this general-purpose skill may be insufficient without a custom, domain-tuned model.
*   **As a Substitute for Fact-Checking**: The skill extracts *mentions* of entities; it does not verify the truthfulness of claims about those entities.

**Typical Downstream Nodes**:
*   `relationship_mapping` (to establish links between extracted entities).
*   `data_enrichment` or `web_search` (to gather more information on a specific extracted organization or person).
*   `report_generation` (to populate structured sections of a report with key actors and locations).
*   `knowledge_graph_update` (to add entity nodes to a graph).

## Constraints

*   **Input Token Limit**: The skill is constrained by the LLM's context window. For extremely long documents, the Planner **must** implement an upstream `chunking` strategy and may need to run this skill on each chunk, followed by a deduplication step.
*   **Hallucination Prohibition**: The skill must **only** extract entities that are explicitly mentioned in the provided source text. It must not infer or invent entities based on world knowledge (e.g., seeing "the President" and outputting "Joe Biden" unless the full name is in the text).
*   **Scope Limitation**: The analysis must be confined strictly to the text provided as input. Do not use external knowledge bases or live lookups to identify or disambiguate entities unless explicitly directed by a separate skill call.
*   **Type Adherence**: The skill must limit entity types to a standard set (Person, Organization, Location, Date, etc.). It should not create new, ad-hoc types. If the source text contains an ambiguous entity, it should choose the most likely standard type or default to "MISC" (Miscellaneous).
*   **Output Format Strictness**: The output **must** conform exactly to the `AnalysisOutput` contract. The `mentions` array should contain the exact string(s) found in the text, and the `context` should be a direct excerpt, not a paraphrase.

## Execution Model

LLM-based

**Prompt file**: `prompts/entity_extraction.md`

## Output Contract

AnalysisOutput — entities: [{entity, type, mentions, context}]