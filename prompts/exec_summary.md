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
    {"bottom_line": "one sentence answer"},
    {"key_evidence": ["point 1", "point 2", "point 3"]},
    {"limitation": "one limitation"},
    {"next_step": "recommended action"}
  ],
  "citations_used": ["[Smith2024]"],
  "confidence": 0.85,
  "coverage_gaps": [],
  "upstream_slots_consumed": ["slot1"]
}
