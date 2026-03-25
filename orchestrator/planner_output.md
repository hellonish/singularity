{
  "metadata": {
    "research_type": "exploratory",
    "core_goal": "Investigate spurious correlations in machine learning across multiple perspectives, ensuring comprehensive coverage and high evidence quality through verification and analysis",
    "domain": "ml_research",
    "audience": "expert",
    "output_format": "report_generator",
    "output_language": "en",
    "depth_default": "deep",
    "recency_window_years": 2,
    "termination_signal": "Coverage of at least 5 perspectives on spurious correlations, with verified claims from multiple sources, meta-analysis of findings, and no unresolved contradictions",
    "node_count": 15,
    "sensitivity_flag": false,
    "multilingual": false,
    "created_at_mode": "plan",
    "replan_round": 0
  },
  "nodes": [
    {
      "node_id": "n1",
      "description": "Search academic literature for definitions and theoretical foundations of spurious correlations in machine learning",
      "skill": "academic_search",
      "depends_on": [],
      "acceptance": ["factual_grounding", "source_authority", "methodological_soundness"],
      "parallelizable": true,
      "output_slot": "definitions_foundations",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n2",
      "description": "Search case studies and real-world examples of spurious correlations in ML applications, such as image recognition or predictive modeling",
      "skill": "web_search",
      "depends_on": [],
      "acceptance": ["factual_grounding", "replication_status", "relevance"],
      "parallelizable": true,
      "output_slot": "case_studies_examples",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n3",
      "description": "Search statistical perspectives on spurious correlations, including confounding variables and correlation vs. causation debates",
      "skill": "academic_search",
      "depends_on": [],
      "acceptance": ["source_authority", "methodological_soundness", "cross_validation"],
      "parallelizable": true,
      "output_slot": "statistical_perspectives",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n4",
      "description": "Search neural network-specific instances of spurious correlations, focusing on deep learning models and feature engineering",
      "skill": "code_search",
      "depends_on": [],
      "acceptance": ["factual_grounding", "replication_status", "depth"],
      "parallelizable": true,
      "output_slot": "neural_network_perspectives",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n5",
      "description": "Search ethical and societal impacts of spurious correlations in ML, including bias amplification and decision-making consequences",
      "skill": "web_search",
      "depends_on": [],
      "acceptance": ["source_authority", "relevance", "conflict_of_interest"],
      "parallelizable": true,
      "output_slot": "ethical_societal_impact",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n6",
      "description": "Search detection methods and tools for spurious correlations, such as causal inference techniques and validation frameworks",
      "skill": "academic_search",
      "depends_on": [],
      "acceptance": ["factual_grounding", "methodological_soundness", "cross_validation"],
      "parallelizable": true,
      "output_slot": "detection_methods",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n7",
      "description": "Search mitigation strategies for spurious correlations, including dataset augmentation and model regularization approaches",
      "skill": "dataset_search",
      "depends_on": [],
      "acceptance": ["replication_status", "relevance", "depth"],
      "parallelizable": true,
      "output_slot": "mitigation_strategies",
      "depth_override": "deep",
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n8",
      "description": "Verify key claims from retrieved sources on spurious correlations using established fact-checking and evidence standards",
      "skill": "claim_verification",
      "depends_on": ["n1", "n2", "n3", "n4", "n5", "n6", "n7"],
      "acceptance": ["factual_grounding", "cross_validation", "coherence"],
      "parallelizable": false,
      "output_slot": "verified_claims",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n9",
      "description": "Detect contradictions across sources on perspectives of spurious correlations, such as conflicting detection methods",
      "skill": "contradiction_detect",
      "depends_on": ["n8"],
      "acceptance": ["coherence", "coverage", "methodological_soundness"],
      "parallelizable": false,
      "output_slot": "contradictions_identified",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n10",
      "description": "Perform meta-analysis on aggregated data from verified sources to synthesize overall patterns in spurious correlations research",
      "skill": "meta_analysis",
      "depends_on": ["n8", "n9"],
      "acceptance": ["source_authority", "cross_validation", "depth"],
      "parallelizable": false,
      "output_slot": "meta_analysis_results",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n11",
      "description": "Conduct gap analysis to identify underrepresented perspectives or limitations in the current research on spurious correlations",
      "skill": "gap_analysis",
      "depends_on": ["n10"],
      "acceptance": ["coverage", "relevance", "coherence"],
      "parallelizable": false,
      "output_slot": "research_gaps",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n12",
      "description": "Generate a comparative analysis of different perspectives on spurious correlations, highlighting strengths and weaknesses",
      "skill": "comparative_analysis",
      "depends_on": ["n11"],
      "acceptance": ["coherence", "relevance", "methodological_soundness"],
      "parallelizable": false,
      "output_slot": "comparative_perspectives",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n13",
      "description": "Synthesize findings into a cohesive narrative, integrating all perspectives and evidence quality assessments",
      "skill": "synthesis",
      "depends_on": ["n12"],
      "acceptance": ["coverage", "coherence", "depth"],
      "parallelizable": false,
      "output_slot": "synthesized_narrative",
      "depth_override": null,
      "synthesis_hint": "Use technical terminology appropriate for experts; provide in-depth explanations and references; emphasize evidence-based conclusions.",
      "note": null
    },
    {
      "node_id": "n14",
      "description": "Generate a bibliography of all sources used, ensuring proper citation and authority checks",
      "skill": "bibliography_gen",
      "depends_on": ["n13"],
      "acceptance": ["factual_grounding", "source_authority", "relevance"],
      "parallelizable": false,
      "output_slot": "source_bibliography",
      "depth_override": null,
      "synthesis_hint": null,
      "note": null
    },
    {
      "node_id": "n15",
      "description": "Compile final report with all synthesized content, including appendices for detailed analyses",
      "skill": "report_generator",
      "depends_on": ["n13", "n14"],
      "acceptance": ["coverage", "relevance", "audience_calibration"],
      "parallelizable": false,
      "output_slot": "final_report",
      "depth_override": null,
      "synthesis_hint": "Tailor for experts: include mathematical derivations where relevant, avoid oversimplification, and highlight implications for ML practice.",
      "note": null
    }
  ]
}

## Intent

**Research type**: exploratory
**Core goal**: Investigate spurious correlations in machine learning across multiple perspectives, ensuring comprehensive coverage and high evidence quality through verification and analysis
**Domain**: ml_research — ML / AI Research
**Domain confidence**: high
**Audience**: expert
**Output format**: report_generator
**Output language**: en
**Implicit constraints**: 
- Deep technical depth required
- Coverage of at least 5 distinct perspectives (e.g., definitions, examples, statistical views, ethical impacts, detection methods)
- Focus on evidence quality with mandatory analysis nodes
**Sensitivity flag**: false — none

## Scope

**Source types active**: academic_search, web_search, code_search, dataset_search
**Depth default**: deep
**Recency window**: 2 years
**Multilingual**: false
**Termination signal**: Coverage of at least 5 perspectives on spurious correlations, with verified claims from multiple sources, meta-analysis of findings, and no unresolved contradictions
**Budget**: expansive (15 nodes)

## Rubric Summary

n1 | academic_search | factual_grounding,source_authority,methodological_soundness  
n2 | web_search | factual_grounding,replication_status,relevance  
n3 | academic_search | source_authority,methodological_soundness,cross_validation  
n4 | code_search | factual_grounding,replication_status,depth  
n5 | web_search | source_authority,relevance,conflict_of_interest  
n6 | academic_search | factual_grounding,methodological_soundness,cross_validation  
n7 | dataset_search | replication_status,relevance,depth  
n8 | claim_verification | factual_grounding,cross_validation,coherence  
n9 | contradiction_detect | coherence,coverage,methodological_soundness  
n10 | meta_analysis | source_authority,cross_validation,depth  
n11 | gap_analysis | coverage,relevance,coherence  
n12 | comparative_analysis | coherence,relevance,methodological_soundness  
n13 | synthesis | coverage,coherence,depth  
n14 | bibliography_gen | factual_grounding,source_authority,relevance  
n15 | report_generator | coverage,relevance,audience_calibration

## Execution Notes

- First parallel wave composition: Nodes n1 through n7 are parallelizable and can execute simultaneously as they have no dependencies.
- Critical path: Longest dependency chain is n1/n2/n3/n4/n5/n6/n7 → n8 → n9 → n10 → n11 → n12 → n13 → n14 → n15, spanning all 15 nodes.
- Bottleneck node(s): n8 (claim_verification) as it depends on all prior nodes, potentially creating a sequential choke point.
- Domain-specific risks: Access barriers to academic sources (e.g., paywalls for journals); rapid evolution in ML research may require cross-validation to mitigate outdated findings.
- Sensitivity or disclaimer notes: None applicable, as sensitivity flag is false.