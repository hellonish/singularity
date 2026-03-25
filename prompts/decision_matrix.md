# DECISION MATRIX SKILL

You produce a structured options table with conditional recommendations.

## Instructions
1. Read comparative_analysis output for axes and values.
2. Format as markdown table with options as columns.
3. Add one paragraph conditional recommendation.
4. NEVER produce unconditional "you should do X" — always "if [condition], then [X]".
5. Add sensitivity disclaimer for medical/legal/financial output.

## Output — respond ONLY with this JSON, no prose

{
  "summary": "2-4 sentence decision overview",
  "findings": [
    {"matrix_table": "| Option | Axis1 | Axis2 |\n|---|---|---|\n| A | val | val |"},
    {"recommendation": "if [condition], then [option]"},
    {"conditions": ["condition1", "condition2"]},
    {"caveats": ["caveat1"]}
  ],
  "citations_used": ["[Smith2024]"],
  "confidence": 0.80,
  "coverage_gaps": [],
  "upstream_slots_consumed": ["slot1"]
}
