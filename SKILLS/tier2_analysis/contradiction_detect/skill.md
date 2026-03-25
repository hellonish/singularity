# contradiction_detect

**Tier**: analysis  
**Name**: `contradiction_detect`  

## Description

Flags pairs of claims that contradict each other across sources.

## When to Use

When cross-source consistency must be verified before synthesis.

## Execution Model

LLM-based

**Prompt file**: `prompts/contradiction_detect.md`

## Output Contract

AnalysisOutput — contradictions: [{claim, source_a, source_b, type, severity}]

## Constraints

- Does NOT resolve contradictions — only flags them
- type: factual | methodological | interpretive
