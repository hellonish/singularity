# annotation_gen

**Tier**: output  
**Name**: `annotation_gen`  

## Description

Produces annotated bibliography: one critical note per source.

## When to Use

Academic research when source-by-source critical analysis is needed.

## Execution Model

LLM-based

**Prompt file**: `prompts/annotation_gen.md`

## Output Contract

OutputDocument — list of {citation_id, formatted_citation, annotation}

## Constraints

- Annotation must address: contribution, authority, limitations (sample, jurisdiction, recency, funding)
