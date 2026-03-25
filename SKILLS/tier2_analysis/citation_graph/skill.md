# citation_graph

**Tier**: analysis  
**Name**: `citation_graph`  

## Description

Maps citation relationships between sources in the CitationRegistry.

## When to Use

Academic research where citation impact or lineage is relevant.

## Execution Model

LLM-based + CitationRegistry data

**Prompt file**: `prompts/citation_graph.md`

## Output Contract

AnalysisOutput — edges: [{citing_id, cited_id, relationship}], clusters: [...]

## Constraints

- Only surfaces citations already registered in ctx.citation_registry
