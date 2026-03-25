# hypothesis_gen

**Tier**: analysis  
**Name**: `hypothesis_gen`  

## Description

Generates testable hypotheses based on current evidence gaps.

## When to Use

Research planning, gap bridging, when gap_analysis identifies unknowns.

## Execution Model

LLM-based

**Prompt file**: `prompts/hypothesis_gen.md`

## Output Contract

AnalysisOutput — hypotheses: [{hypothesis, rationale, testability_score, suggested_test}]

## Constraints

- Must root hypotheses in evidence from ctx; no fabrication
