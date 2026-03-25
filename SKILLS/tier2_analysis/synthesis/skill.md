# synthesis

**Tier**: analysis  
**Name**: `synthesis`  

## Description

Combines findings from multiple upstream sources into a coherent narrative.

## When to Use

After 2+ retrieval nodes have completed. Central analysis step.

## Execution Model

LLM-based (grok model)

**Prompt file**: `prompts/synthesis.md`

## Output Contract

AnalysisOutput — findings list of {claim, supporting_citations, confidence, hedging_note}

## Constraints

- Must not introduce claims not present in upstream sources
- Follow synthesis_hint from node metadata strictly
