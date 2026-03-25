# quality_check

**Tier**: analysis  
**Name**: `quality_check`  

## Description

Evaluates whether a node's output satisfies its acceptance axes.

## When to Use

After any retrieval or analysis node whose output quality must be gated.

## Execution Model

LLM-based

**Prompt file**: `prompts/quality_check.md`

## Output Contract

QualityReport — {axes_evaluated, results: {axis: {passed, score, reason, threshold}}, overall_pass, remediation_suggestion}

## Constraints

- Threshold 0.80 for factual_grounding; domain-specific for others
- If overall_pass=False → orchestrator generates GapItem automatically
