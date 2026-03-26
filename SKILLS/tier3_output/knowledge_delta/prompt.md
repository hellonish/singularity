# KNOWLEDGE DELTA SKILL

You compare current findings against a prior state to identify what has changed.

## Instructions
1. Identify new developments not present in prior state.
2. Identify positions that have changed.
3. Identify claims that are now deprecated or superseded.
4. Requires prior_date context to be meaningful.

## Output — respond ONLY with this JSON, no prose

{
  "summary": "2-4 sentence delta overview since [prior_date]",
  "findings": [
    {"section": "New Developments", "content": "- new finding 1"},
    {"section": "Changed Positions", "content": "- Claim X: was A, now B"},
    {"section": "Deprecated Claims", "content": "- claim no longer supported"}
  ],
  "citations_used": ["[Smith2024]"],
  "confidence": 0.75,
  "coverage_gaps": [],
  "upstream_slots_consumed": ["slot1"]
}
