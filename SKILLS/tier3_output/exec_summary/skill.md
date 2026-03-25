# exec_summary

**Tier**: output  
**Name**: `exec_summary`  

## Description

Produces a concise executive summary: bottom line, 3 evidence bullets, limitation, next step.

## When to Use

When plan output_format is 'exec_summary' or as sensitivity disclaimer wrapper.

## Execution Model

LLM-based

**Prompt file**: `prompts/exec_summary.md`

## Output Contract

OutputDocument — {bottom_line, key_evidence[3], limitation, next_step}

## Constraints

- Maximum 350 words
- Bottom line in first sentence
