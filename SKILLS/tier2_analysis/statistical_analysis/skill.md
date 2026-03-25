# statistical_analysis

**Tier**: analysis  
**Name**: `statistical_analysis`  

## Description

Computes descriptive statistics from extracted tabular data.

## When to Use

When data_extraction has produced numerical tables.

## Execution Model

LLM-based + Python computation

**Prompt file**: `prompts/statistical_analysis.md`

## Output Contract

AnalysisOutput — stats: [{variable, mean, median, range, n, unit}]

## Constraints

- Never fabricate statistics
- State explicitly if data is insufficient
