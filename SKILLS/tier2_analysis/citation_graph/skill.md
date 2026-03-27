# citation_graph

**Tier**: analysis  
**Name**: `citation_graph`  

## Description

This skill performs a sophisticated network analysis on the citation relationships stored within the active context's `CitationRegistry`. It physically processes the registry's data to construct a directed graph model where nodes represent individual sources (e.g., academic papers, reports, articles) and edges represent citation relationships between them. The cognitive process involves the LLM interpreting the semantic context and stated relationships within each source's metadata to infer the *nature* of the citation beyond a simple link (e.g., supportive, contradictory, foundational). The skill applies specific data transformations: it ingests the flat list of citation objects from the registry, identifies all `source_id` and `cited_id` pairs, and for each pair, prompts the LLM to analyze the textual context from the citing source to classify the relationship. It then performs a basic graph analysis to identify clusters or communities of densely interconnected sources, which may represent sub-fields, competing theories, or evolutionary lineages of thought. The final output is a structured network model containing nodes, annotated edges, and identified clusters, ready for visualization or further quantitative analysis.

## When to Use

- **Specific Scenarios**:
    1.  When a user asks to "map the intellectual lineage," "show the citation network," or "visualize how these papers are connected."
    2.  During literature review synthesis to understand the influence and dialogue between key papers.
    3.  To identify central (highly cited) papers or pivotal papers that connect disparate clusters.
    4.  To uncover the structure of a research field, including potential schools of thought or methodological groupings.
    5.  As a preparatory step for generating a narrative or report on the evolution of an idea.

- **Upstream Dependencies**:
    - This skill **MUST** be preceded by skills that populate the `ctx.citation_registry` (e.g., `search_academic`, `extract_citations`, `analyze_paper`). It expects the registry to contain multiple source objects, each with a unique `id` and a `citations` list containing `id`s of other sources. The raw text or context of the citation statement is highly beneficial for relationship classification.

- **When NOT to Use (Edge Cases)**:
    1.  **Do NOT use** if `ctx.citation_registry` is empty or contains fewer than two sources with citation links. A graph cannot be formed.
    2.  **Avoid using** for simple bibliography generation; use `format_citations` instead.
    3.  **Do NOT use** to *find* new citations; it only analyzes those already logged in the registry.
    4.  **Ineffective** for analyzing a single paper in isolation; requires a multi-source corpus.

- **Downstream Nodes**:
    - Typically followed by `visualize_data` (to render the graph), `summarize_analysis` (to narrate findings), or `report_writer` (to incorporate network insights into a final document).

## Execution Model

LLM-based + CitationRegistry data

**Prompt file**: `prompts/citation_graph.md`

## Output Contract

AnalysisOutput — edges: [{citing_id, cited_id, relationship}], clusters: [...]

## Constraints

1.  **Registry Scope**: This skill is **STRICTLY LIMITED** to analyzing citation relationships that are already explicitly registered in `ctx.citation_registry`. It cannot hallucinate, infer, or search for citations not present in the registry data. The Planner must ensure the registry is populated first.
2.  **Relationship Classification**: The LLM must base its `relationship` classification (e.g., "supports," "contradicts," "extends," "uses_methodology_of") **solely** on the context snippet provided from the citing source. It must avoid over-interpretation or applying external knowledge not present in the provided text.
3.  **Graph Scale**: For very large registries (e.g., >50 sources with complex interlinks), be aware of potential token limits when the LLM is prompted to consider the entire network. The skill implementation may process in batches, but the Planner should be cautious of context window overflows.
4.  **No External Analysis**: The skill performs the network *construction* and *semantic edge annotation*. It does not perform advanced graph metrics (e.g., betweenness centrality, PageRank) unless explicitly coded; the `clusters` output is based on connected components or simple community detection. Do not assume it provides deep statistical analysis.
5.  **Idempotency**: Given the same `CitationRegistry` state, the output should be functionally identical. The Planner should not call it repeatedly without registry changes.