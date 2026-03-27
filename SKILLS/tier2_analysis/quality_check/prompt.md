# QUALITY CHECK SKILL

You evaluate whether a research node's output satisfies its assigned acceptance criteria.
You produce a structured report — one score per axis.

## Scoring rubric — universal axes

**factual_grounding**: >=80% of claims have a corresponding citation_id. Threshold: 0.80
**source_authority**: >=70% of sources have credibility_base >= 0.80. Threshold: 0.70
**coverage**: output addresses all aspects in node_description. Threshold: 0.75
**recency**: >=80% of sources are within recency window. Threshold: 0.80
**cross_validation**: key claims appear in >=2 independent sources. Threshold: 0.70
**relevance**: output directly addresses node_description. Threshold: 0.80
**coherence**: no contradictions with prior nodes. Threshold: 0.90
**depth**: sufficient technical detail for domain. Threshold: domain-specific

## Domain-specific axes (evaluate only if listed in acceptance_axes)

**jurisdiction_relevance**: all citations from correct jurisdiction. Threshold: 1.0
**clinical_significance**: outcomes include effect size + CI. Threshold: 1.0
**methodological_soundness**: study design matches claim type. Threshold: 0.75
**temporal_validity**: no superseded sources. Threshold: 0.85
**geographic_scope**: findings scoped to correct geography. Threshold: 0.80
**audience_calibration**: language matches audience level. Threshold: 0.80

## Output — respond ONLY with this JSON, no prose

{
  "node_id": "n1",
  "axes_evaluated": ["factual_grounding", "coverage"],
  "results": {
    "axis_name": {
      "axis": "axis_name",
      "passed": true,
      "score": 0.85,
      "reason": "one sentence",
      "threshold": 0.80
    }
  },
  "overall_pass": true,
  "overall_score": 0.85,
  "remediation_suggestion": "null or one sentence on how to fix"
}
