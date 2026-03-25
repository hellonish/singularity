# decision_matrix

**Tier**: output  
**Name**: `decision_matrix`  

## Description

Produces a structured options table with conditional recommendation.

## When to Use

When plan output_format is 'decision_matrix'. Especially in legal/finance/product domains.

## Execution Model

LLM-based

**Prompt file**: `prompts/decision_matrix.md`

## Output Contract

OutputDocument — {matrix_table (markdown), recommendation, conditions, caveats}

## Constraints

- Never unconditional 'you should do X' — always 'if [condition], then [X]'
- Sensitivity disclaimer mandatory for medical/legal/financial
