# knowledge_delta

**Tier**: output  
**Name**: `knowledge_delta`  

## Description

Compares current findings against a prior state to identify what has changed.

## When to Use

Monitoring, recurring research runs. Requires prior_date in plan metadata.

## Execution Model

LLM-based

**Prompt file**: `prompts/knowledge_delta.md`

## Output Contract

OutputDocument — {new_developments, changed_positions, deprecated_claims}

## Constraints

- Requires prior_date ISO in plan metadata
- Deprecated claims must be explicitly marked
