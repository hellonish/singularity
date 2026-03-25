# trend_analysis

**Tier**: analysis  
**Name**: `trend_analysis`  

## Description

Identifies directional trends across time-series data or dated sources.

## When to Use

Market analysis, technology adoption, epidemiological trends.

## Execution Model

LLM-based

**Prompt file**: `prompts/trend_analysis.md`

## Output Contract

AnalysisOutput — trends: [{dimension, direction, evidence, confidence}]

## Constraints

- Require dated sources; decline to identify trend if sources lack dates
