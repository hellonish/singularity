# entity_extraction

**Tier**: analysis  
**Name**: `entity_extraction`  

## Description

Identifies named entities (people, organisations, places, dates) in upstream text.

## When to Use

When subsequent nodes need structured entity data.

## Execution Model

LLM-based

**Prompt file**: `prompts/entity_extraction.md`

## Output Contract

AnalysisOutput — entities: [{entity, type, mentions, context}]
