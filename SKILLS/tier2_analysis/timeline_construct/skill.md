# timeline_construct

**Tier**: analysis  
**Name**: `timeline_construct`  

## Description

Constructs a chronological timeline of events from upstream sources.

## When to Use

Historical analysis, event sequencing, policy evolution.

## Execution Model

LLM-based

**Prompt file**: `prompts/timeline_construct.md`

## Output Contract

AnalysisOutput — events: [{date, event, source_citation, confidence}]

## Constraints

- Only include events with a cited source
- Flag uncertain dates with '~'
