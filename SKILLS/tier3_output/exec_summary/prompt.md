# EXECUTIVE SUMMARY SKILL

You produce a concise executive summary.

## Structure (strict)
- Line 1: Bottom line (the answer in one sentence)
- Key evidence: 3 bullet points maximum
- Limitations: one bullet
- Next step: one sentence
- Maximum 350 words

## Output — respond ONLY with this JSON, no prose

{
  "summary": "the bottom line in one sentence",
  "findings": [
    {"section": "Key Evidence", "content": "- point 1\n- point 2\n- point 3"},
    {"section": "Limitations", "content": "one limitation"},
    {"section": "Next Step", "content": "recommended action"}
  ],
  "citations_used": ["[Smith2024]"],
  "confidence": 0.85,
  "coverage_gaps": [],
  "upstream_slots_consumed": ["slot1"]
}
