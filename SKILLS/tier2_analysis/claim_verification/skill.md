# claim_verification

**Tier**: analysis  
**Name**: `claim_verification`  

## Description

Verifies key claims in synthesis output against their cited sources.

## When to Use

After synthesis, when factual accuracy must be validated.

## Execution Model

LLM-based

**Prompt file**: `prompts/claim_verification.md`

## Output Contract

AnalysisOutput — verifications: [{claim, verified, supporting, contradicting, verdict}]

## Constraints

- Must check actual citation content, not just presence of citation_id
