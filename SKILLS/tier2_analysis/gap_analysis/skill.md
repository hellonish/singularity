# gap_analysis

**Tier**: analysis  
**Name**: `gap_analysis`  

## Description

Identifies what the current research plan has NOT covered vs. the termination signal.

## When to Use

After at least one round of retrieval. Input to replanning.

## Execution Model

LLM-based

**Prompt file**: `prompts/gap_analysis.md`

## Output Contract

AnalysisOutput — gaps: [{gap_description, severity, suggested_node}]

## Constraints

- Compare against plan.metadata.termination_signal
- severity: critical | moderate | minor
