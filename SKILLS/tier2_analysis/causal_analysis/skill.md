# causal_analysis

**Tier**: analysis  
**Name**: `causal_analysis`  

## Description

Distinguishes correlation from causation and documents causal evidence.

## When to Use

When the plan requires understanding cause-effect relationships.

## Execution Model

LLM-based

**Prompt file**: `prompts/causal_analysis.md`

## Output Contract

AnalysisOutput — claims: [{claim, evidence_type, confounders_noted, strength}]

## Constraints

- evidence_type: RCT | observational | mechanistic | expert_opinion
- If no RCT evidence for causal claim → mandatory note in findings
