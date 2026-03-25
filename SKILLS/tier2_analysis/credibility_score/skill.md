# credibility_score

**Tier**: analysis  
**Name**: `credibility_score`  

## Description

Aggregates and evaluates credibility of upstream sources.

## When to Use

After retrieval nodes, before high-stakes synthesis. Always in medical/legal/finance.

## Execution Model

Deterministic Python (reads ctx.credibility_scores)

## Output Contract

AnalysisOutput — {avg_credibility, conflict_of_interest_flag, recommendation, scores_by_slot}

## Constraints

- avg < 0.65 → PARTIAL status; < 0.50 → FAILED
