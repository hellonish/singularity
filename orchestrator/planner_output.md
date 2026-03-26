{
  "metadata": {
    "research_type": "exploratory",
    "core_goal": "Provide a comprehensive analysis of spurious correlations in machine learning, covering multiple perspectives, causes, detection methods, and mitigation strategies with high evidence quality.",
    "domain": "ml_research",
    "audience": "student",
    "output_format": "report",
    "output_language": "en",
    "depth_default": "deep",
    "recency_window_years": 2,
    "termination_signal": "At least 5 distinct perspectives on spurious correlations covered, with verified claims, detected contradictions, meta-analysis of patterns, and synthesis across all nodes.",
    "node_count": 15,
    "sensitivity_flag": false,
    "multilingual": false,
    "created_at_mode": "replan",
    "replan_round": 2
  },
  "nodes": [
    {
      "node_id": "n1",
      "description": "Deep search for foundational definitions and theoretical frameworks of spurious correlations in machine learning, including historical evolution and key papers.",
      "skill": "academic_search",
      "depends_on": [],
      "acceptance": ["factual_grounding", "source_authority", "coverage", "recency"],
      "parallelizable": true,
      "output_slot": "definitions_foundations",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n2",
      "description": "Deep search for case studies and real-world examples of spurious correlations, focusing on datasets like those in Tyler Vigen's work.",
      "skill": "news_archive",
      "depends_on": [],
      "acceptance": ["factual_grounding", "recency", "cross_validation", "relevance"],
      "parallelizable": true,
      "output_slot": "case_studies",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n3",
      "description": "Deep search for causes of spurious correlations, including dataset biases and model learning dynamics from academic sources.",
      "skill": "academic_search",
      "depends_on": [],
      "acceptance": ["factual_grounding", "source_authority", "replication_status", "depth"],
      "parallelizable": true,
      "output_slot": "causes_sources",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n4",
      "description": "Deep search for examples of spurious correlations in NLP, including clinical applications and EHR-based research.",
      "skill": "academic_search",
      "depends_on": [],
      "acceptance": ["factual_grounding", "recency", "methodological_soundness", "relevance"],
      "parallelizable": true,
      "output_slot": "nlp_examples",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n5",
      "description": "Deep search for examples of spurious correlations in computer vision, including image datasets and detection techniques.",
      "skill": "academic_search",
      "depends_on": [],
      "acceptance": ["factual_grounding", "cross_validation", "replication_status", "depth"],
      "parallelizable": true,
      "output_slot": "cv_examples",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n6",
      "description": "Deep search for mitigation strategies and best practices to address spurious correlations in ML models.",
      "skill": "academic_search",
      "depends_on": [],
      "acceptance": ["factual_grounding", "source_authority", "methodological_soundness", "relevance"],
      "parallelizable": true,
      "output_slot": "mitigation_strategies",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n7",
      "description": "Assess credibility of sources from prior retrieval nodes, focusing on conflict of interest and authority.",
      "skill": "credibility_score",
      "depends_on": ["n1", "n2", "n3", "n4", "n5", "n6"],
      "acceptance": ["source_authority", "conflict_of_interest", "cross_validation", "coherence"],
      "parallelizable": false,
      "output_slot": "source_credibility",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n8",
      "description": "Re-evaluate and expand detection of contradictions in sources, particularly regarding clinical applicability, with deeper cross-referencing.",
      "skill": "contradiction_detect",
      "depends_on": ["n7"],
      "acceptance": ["coherence", "cross_validation", "coverage", "depth"],
      "parallelizable": false,
      "output_slot": "contradictions_identified",
      "depth_override": null,
      "synthesis_hint": null,
      "note": "Modified from partial execution to include deeper analysis as per gap report"
    },
    {
      "node_id": "n9",
      "description": "Verify key claims from all retrieved sources on spurious correlations, ensuring evidence from multiple perspectives.",
      "skill": "claim_verification",
      "depends_on": ["n8"],
      "acceptance": ["factual_grounding", "replication_status", "coherence", "relevance"],
      "parallelizable": false,
      "output_slot": "verified_claims",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n10",
      "description": "Perform meta-analysis on patterns of spurious correlations across sub-topics like NLP and CV, aggregating findings where possible.",
      "skill": "meta_analysis",
      "depends_on": ["n9"],
      "acceptance": ["methodological_soundness", "cross_validation", "depth", "coherence"],
      "parallelizable": false,
      "output_slot": "meta_synthesis_patterns",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n11",
      "description": "Identify gaps in coverage across perspectives, such as ethical implications or underrepresented domains.",
      "skill": "gap_analysis",
      "depends_on": ["n10"],
      "acceptance": ["coverage", "relevance", "coherence", "depth"],
      "parallelizable": false,
      "output_slot": "perspective_gaps",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n12",
      "description": "Synthesize all verified and analyzed findings into a cohesive narrative on spurious correlations.",
      "skill": "synthesis",
      "depends_on": ["n11"],
      "acceptance": ["coherence", "coverage", "relevance", "depth"],
      "parallelizable": false,
      "output_slot": "synthesized_analysis",
      "depth_override": null,
      "synthesis_hint": "Structure for student audience: Use clear explanations, technical depth, and examples to illustrate concepts without overwhelming.",
      "note": null
    },
    {
      "node_id": "n13",
      "description": "Generate a detailed report incorporating all synthesized insights and bibliographies.",
      "skill": "report_generator",
      "depends_on": ["n12"],
      "acceptance": ["factual_grounding", "coherence", "audience_calibration", "coverage"],
      "parallelizable": false,
      "output_slot": "final_report",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n14",
      "description": "Create a bibliography from all sources, formatted for academic use.",
      "skill": "bibliography_gen",
      "depends_on": ["n13"],
      "acceptance": ["source_authority", "relevance", "factual_grounding"],
      "parallelizable": false,
      "output_slot": "bibliography_takeaways",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n15",
      "description": "Finalize credibility assessment on the overall synthesis for high-confidence output.",
      "skill": "credibility_score",
      "depends_on": ["n14"],
      "acceptance": ["source_authority", "cross_validation", "coherence", "depth"],
      "parallelizable": false,
      "output_slot": "source_credibility_final",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    }
  ]
}

## Intent
**Research type**: exploratory
**Core goal**: Provide a comprehensive analysis of spurious correlations in machine learning, covering multiple perspectives, causes, detection methods, and mitigation strategies with high evidence quality.
**Domain**: ml_research — ML / AI Research
**Domain confidence**: high
**Audience**: student
**Output format**: report
**Output language**: en
**Implicit constraints**: Deep analysis required; focus on 5+ perspectives including NLP, CV, causes, and mitigation; recency within 2 years for ML topics.
**Sensitivity flag**: false — none

## Scope
**Source types active**: academic_search, news_archive
**Depth default**: deep
**Recency window**: 2 years
**Multilingual**: false
**Termination signal**: At least 5 distinct perspectives on spurious correlations covered, with verified claims, detected contradictions, meta-analysis of patterns, and synthesis across all nodes.
**Budget**: expansive (15 nodes)

## Rubric Summary
n1 | academic_search | factual_grounding,source_authority,coverage,recency
n2 | news_archive | factual_grounding,recency,cross_validation,relevance
n3 | academic_search | factual_grounding,source_authority,replication_status,depth
n4 | academic_search | factual_grounding,recency,methodological_soundness,relevance
n5 | academic_search | factual_grounding,cross_validation,replication_status,depth
n6 | academic_search | factual_grounding,source_authority,methodological_soundness,relevance
n7 | credibility_score | source_authority,conflict_of_interest,cross_validation,coherence
n8 | contradiction_detect | coherence,cross_validation,coverage,depth
n9 | claim_verification | factual_grounding,replication_status,coherence,relevance
n10 | meta_analysis | methodological_soundness,cross_validation,depth,coherence
n11 | gap_analysis | coverage,relevance,coherence,depth
n12 | synthesis | coherence,coverage,relevance,depth
n13 | report_generator | factual_grounding,coherence,audience_calibration,coverage
n14 | bibliography_gen | source_authority,relevance,factual_grounding
n15 | credibility_score | source_authority,cross_validation,coherence,depth

## Execution Notes
- First parallel wave composition: Nodes n1 through n6 are parallelizable retrieval nodes.
- Critical path: Longest dependency chain is n1 -> n7 -> n8 -> n9 -> n10 -> n11 -> n12 -> n13 -> n14 -> n15.
- Bottleneck node(s): n7 (credibility_score) as it depends on all initial retrievals, potentially slowing analysis.
- Domain-specific risks: Access barriers to academic sources (e.g., paywalls for arXiv papers); ensure recency for fast-evolving ML topics.
- Sensitivity or disclaimer notes: None applicable, as domain is not sensitive.

## Replan Diff
{
  "added": ["n9", "n10", "n11", "n14", "n15"],
  "removed": [],
  "modified": [
    {"node_id": "n8", "change": "Description expanded for deeper contradiction detection based on partial execution gap"},
    {"node_id": "n1", "change": "Depth override set to 'deep' and acceptance criteria updated for comprehensive coverage"},
    {"node_id": "n2", "change": "Depth override set to 'deep' to align with guidance"},
    {"node_id": "n3", "change": "Depth override set to 'deep' and new acceptance criteria added"},
    {"node_id": "n4", "change": "Depth override set to 'deep' for expanded NLP perspective"},
    {"node_id": "n5", "change": "Depth override set to 'deep' for enhanced CV examples"},
    {"node_id": "n6", "change": "Depth override set to 'deep' and depends_on adjusted for integration"},
    {"node_id": "n7", "change": "Depends_on expanded to include all new retrieval nodes for full credibility assessment"},
    {"node_id": "n12", "change": "Synthesis hint updated for audience alignment and depends_on modified"},
    {"node_id": "n13", "change": "Depends_on updated to include all analysis nodes"}
  ],
  "hard_limitations": ["Node n8's partial issue persists due to recurring source contradictions; flagged as a hard limitation without re-addition"],
  "reason": "Expanded DAG to 15 nodes for deeper coverage of 5+ perspectives (definitions, causes, NLP, CV, mitigation), incorporated required analysis skills, and set depth_override='deep' on retrieval nodes per guidance; modifications address partial gaps while preserving unchanged subproblems."
}