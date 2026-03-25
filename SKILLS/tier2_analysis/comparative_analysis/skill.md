# comparative_analysis

**Tier**: analysis  
**Name**: `comparative_analysis`  

## Description

Compares two or more subjects across multiple axes.

## When to Use

When the plan requires side-by-side evaluation of options, approaches, or entities.

## Execution Model

LLM-based

**Prompt file**: `prompts/comparative_analysis.md`

## Output Contract

AnalysisOutput — findings: [{axis, values_per_subject, winner_if_any, caveat}]

## Constraints

- Note explicitly when data is insufficient to compare on a given axis
