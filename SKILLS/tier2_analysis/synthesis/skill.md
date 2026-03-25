# synthesis

**Tier**: analysis  
**Name**: `synthesis`  

## Description

The synthesis skill is a core analytical engine that performs high-level cognitive integration of disparate information streams. It physically ingests the outputs from multiple upstream retrieval or analysis nodes, which are typically lists of claims, facts, data points, or evidence snippets, each annotated with source citations. The agent's cognitive process involves a multi-stage analysis: first, it parses and clusters related information from the different sources based on semantic similarity and thematic overlap. Next, it identifies points of consensus, contradiction, or complementary detail across the source material. It then constructs a new, higher-order narrative or argumentative structure that weaves these individual findings together, resolving minor contradictions where possible through logical inference or by noting the discrepancy explicitly. The final output is not a simple concatenation or summary, but a synthesized whole where the relationships between the sourced claims are made explicit, creating a coherent analytical perspective that was not present in any single input source. The specific data transformation applied is from a collection of cited fact-lists into a structured `AnalysisOutput` containing synthesized claims, each explicitly tied back to its foundational sources with appropriate confidence assessments and hedging language.

## When to Use

- **Specific Scenarios**:
    1.  After executing 2 or more parallel `retrieval` nodes (e.g., `retrieval_web`, `retrieval_knowledge_base`) on different aspects of a query, to merge their findings into a single, unified answer.
    2.  Following a `multi_perspective` analysis node, to consolidate the different viewpoints into a balanced summary.
    3.  In the final stages of a research DAG, to combine evidence from primary source analysis, expert commentary retrieval, and data interpretation into a comprehensive report section.
    4.  When a user query is complex and multifaceted, requiring integration of information from several distinct domains or document types.

- **Upstream Dependencies & Input Format**:
    - **Required**: This skill **must** have at least two (2) completed upstream nodes providing data. These are typically nodes with `retrieval` or `analysis` tier outputs.
    - **Expected Input**: The skill expects to receive the outputs from these nodes, which should be structured or semi-structured data containing discrete "claims" or "findings," each ideally associated with one or more source citations (e.g., document IDs, URLs). The data is passed via the execution graph's edge parameters.

- **Edge Cases - When NOT to Use**:
    1.  **Single Source**: Do not use if there is only one source of information. Use a `summarization` or `analysis` skill instead.
    2.  **Raw Data Aggregation**: Do not use for simply merging raw text chunks or long documents without prior extraction of claims/findings. Pre-process with extraction skills first.
    3.  **Fact-Checking a Single Claim**: If the goal is to verify one specific statement, use a `verification` skill against multiple sources, not synthesis.
    4.  **Creative Generation**: Do not use if the task is to generate new ideas, stories, or hypotheses not grounded in the provided source material.

- **Downstream Nodes**:
    - The synthesized `AnalysisOutput` is typically consumed by:
        1.  A `report_writing` or `narrative_building` skill to be turned into prose.
        2.  A `decision_making` node that requires consolidated intelligence.
        3.  A final `answer_formulation` node in a Q&A pipeline.

## Execution Model

LLM-based (grok model)

**Prompt file**: `prompts/synthesis.md`

## Output Contract

AnalysisOutput — findings list of {claim, supporting_citations, confidence, hedging_note}

## Constraints

1.  **Strict Grounding Mandate**: The agent must NOT introduce any new claims, conclusions, or data points that are not directly supported by the provided upstream sources. Every element of the synthesized narrative must be traceable to a citation in the input. Hallucination is strictly forbidden.
2.  **Adherence to Synthesis Hint**: The node metadata may contain a `synthesis_hint` (e.g., "focus on comparing cost implications," "synthesize toward a recommendation"). The agent MUST interpret and strictly follow this directive to shape the narrative and select which aspects of the source material to emphasize.
3.  **Citation Integrity**: Every `claim` in the output list MUST have a `supporting_citations` field populated with the relevant source identifiers from the input. Do not cite sources that were not provided.
4.  **Contradiction Handling**: If sources directly contradict each other on a material point, the synthesis must acknowledge this in the `hedging_note` (e.g., "Sources disagree on X...") rather than silently choosing one side. The `confidence` score should reflect this ambiguity.
5.  **Scope Limitation**: The synthesis is confined to the content provided by the immediate upstream nodes. The agent must not draw upon its internal knowledge to fill gaps or make connections not evidenced in the sources, unless explicitly instructed via the `synthesis_hint` to apply general reasoning.
6.  **Output Structure Compliance**: The output must be a valid `AnalysisOutput` object. Do not return free-form text. The `findings` list should be ordered logically (e.g., by theme, chronology, or importance) to form a coherent narrative flow.