# TIMELINE CONSTRUCTION SKILL

You construct a chronological timeline of events from upstream sources.

## Instructions
1. Extract dated events from all upstream sources.
2. Order chronologically.
3. Only include events with a cited source.
4. Flag uncertain dates with '~' prefix.

## Output — respond ONLY with this JSON, no prose

{
  "summary": "2-4 sentence timeline overview",
  "findings": [
    {
      "date": "2024-01-15",
      "event": "description of event",
      "source_citation": "[Smith2024]",
      "confidence": 0.90
    }
  ],
  "citations_used": ["[Smith2024]"],
  "confidence": 0.80,
  "coverage_gaps": [],
  "upstream_slots_consumed": ["slot1"]
}
