# Retriever — Skill Selection Plan

## System Prompt

You are a retrieval planner. Return ONLY valid JSON — no prose, no markdown fences.
Your JSON must have exactly these two keys: 'skill_selection' and 'skill_queries'.

CRITICAL — query strings are clean web search strings. Rules:
  ✗ NEVER: "India LPG shortage (for Section 3: Geopolitical Context)"
  ✗ NEVER: "supply chain impact [node_id: n5]"
  ✗ NEVER: annotating queries with section IDs or parenthetical notes
  ✓ CORRECT: "India LPG shortage 2026"
  ✓ CORRECT: "Hormuz strait closure LPG supply chain impact"
The 'for_sections' field in each query entry is metadata only — it NEVER appears in the query string itself.

## User Prompt

mode: retrieval_plan
research_query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method. Report Describing your Approach for Realizing the Project
classified_domain_key: ml_research
classified_domain_label: ML / AI Research
classified_domain_confidence: high
Use this as the primary signal for which retrieval skills fit the query; override only if the question clearly contradicts it.

report_sections (25 planned, 18 leaf sections):
  - [n1] Navigating Incorrect Inductive Biases in Deep Learning: A Practitioner’s Report: This report provides a comprehensive guide to understanding, identifying, and ad
  - [n2] Understanding Inductive Biases: Establishes the foundational concepts and definitions of inductive biases, focus
  - [n3] Defining Inductive Bias in Learning Systems: Outlines the core axioms of inductive bias as a preference mechanism in learning
  - [n4] Mathematical Foundations of Bias: Presents the formal mathematical structures underlying inductive biases, showing
  - [n5] Why Biases Lead to Incorrect Generalizations: Explores the properties that cause biases to result in incorrect learning, such 
  - [n6] Illustrative Examples of Incorrect Biases: Provides concrete worked examples and experiments demonstrating incorrect induct
  - [n7] Vision Domain: Background Color Confounding: Details an experiment where a model learns to classify fruits based on backgroun
  - [n8] Language Domain: Shortcut Learning in Text: Illustrates how language models learn superficial patterns, such as specific wor
  - [n9] Cross-Domain Generalization Failures: Analyzes how biases manifest differently across domains and fail to generalize, 
  - [n10] Identifying Bias in Practice: Guides practitioners on when and how to detect incorrect inductive biases in the
  - [n11] Decision Gates for Bias Detection: Explains how to evaluate if a bias is present in model outputs, using diagnostic
  - [n12] Common Failure Modes: Describes top failure modes like spurious correlations and domain shift issues, 
  - [n13] Implementation Strategies for Bias Mitigation: Offers a step-by-step guide for practitioners to implement techniques that addre
  - [n14] Data Preparation and Augmentation: Details preprocessing steps to reduce biases, such as varying data conditions to
  - [n15] Model Training Adjustments: Guides on adjusting architectures and training processes, such as adversarial tr
  - [n16] Integration into Existing Pipelines: Explains how to incorporate bias mitigation into standard deep learning workflow
  - [n17] Solutions to Incorrect Biases: Reviews established methods from literature and proposes a novel approach to mit
  - [n18] Literature Solution: Data Augmentation: Implements data augmentation techniques from key papers to address biases, with 
  - [n19] Literature Solution: Adversarial Training: Details the use of adversarial methods to correct biases, supported by implement
  - [n20] Proposed Novel Method: Suggests a new hybrid approach for bias mitigation, validated through experiment
  - [n21] Validation and Optimization: Covers strategies to measure success, audit bias correction, and optimize perfor
  - [n22] Key Metrics for Success: Defines measurable outcomes like accuracy on unbiased test sets to evaluate bias
  - [n23] Auditing and Verification Techniques: Guides on verifying the absence of bias through sensitivity analysis and automat
  - [n24] Balancing Accuracy and Efficiency: Explains how to optimize computational resources while maintaining effective bia
  - [n25] Future Directions and Challenges: Outlines ongoing challenges and emerging areas for addressing inductive biases i

available_skills: web_search, academic_search, clinical_search, legal_search, financial_search, news_archive, gov_search, code_search, patent_search, standards_search, forum_search, video_search, dataset_search, book_search, social_search, pdf_deep_extract, multimedia_search, data_extraction
select_n_skills: 4  (web_search is always added automatically — do not include it)
queries_per_skill: 4

Return this exact JSON structure:
{
  "skill_selection": {
    "selected": ["skill_name", ...],
    "reasoning": {"skill_name": "why this skill fits this query"}
  },
  "skill_queries": {
    "skill_name": [
      {"query": "clean web search string", "for_sections": ["n1", "n3"]},
      ...
    ]
  }
}

Generate exactly 4 queries per skill. Each query must target one or more specific sections from the list above. Queries within a skill must be semantically diverse — no paraphrases.

## Raw LLM Response

```
{
  "skill_selection": {
    "selected": ["web_search", "academic_search", "dataset_search", "video_search"],
    "reasoning": {
      "web_search": "Fits the query as it provides broad access to general resources on inductive biases in deep learning, covering various sections like definitions and examples.",
      "academic_search": "Fits because the query involves ML research, requiring scholarly papers on inductive biases, experiments, and mitigation strategies.",
      "dataset_search": "Fits for retrieving datasets used in deep learning experiments to illustrate incorrect inductive biases, as per sections on examples and validation.",
      "video_search": "Fits due to the query's reference to a YouTube talk on inductive biases, useful for visual explanations in sections like illustrative examples and domain failures."
    }
  },
  "skill_queries": {
    "web_search": [
      {"query": "incorrect inductive biases in deep learning vision domain", "for_sections": ["n7"]},
      {"query": "language models shortcut learning examples", "for_sections": ["n8"]},
      {"query": "mitigating inductive biases in AI training", "for_sections": ["n13"]},
      {"query": "novel methods for addressing deep learning biases", "for_sections": ["n20"]}
    ],
    "academic_search": [
      {"query": "definition of inductive bias in machine learning", "for_sections": ["n3"]},
      {"query": "experiments on incorrect generalizations in neural networks", "for_sections": ["n6"]},
      {"query": "cross-domain failures of inductive biases", "for_sections": ["n9"]},
      {"query": "adversarial training for bias mitigation in deep learning", "for_sections": ["n19"]}
    ],
    "dataset_search": [
      {"query": "datasets for fruit classification with background variations", "for_sections": ["n7"]},
      {"query": "text datasets with spurious correlations for language models", "for_sections": ["n8"]},
      {"query": "unbiased test sets for deep learning bias evaluation", "for_sections": ["n22"]},
      {"query": "augmented datasets for inductive bias correction", "for_sections": ["n18"]}
    ],
    "video_search": [
      {"query": "inductive biases in deep learning talks", "for_sections": ["n2"]},
      {"query": "examples of bias in vision AI experiments", "for_sections": ["n7"]},
      {"query": "tutorials on detecting inductive biases in models", "for_sections": ["n11"]},
      {"query": "methods to mitigate AI biases in practice", "for_sections": ["n17"]}
    ]
  }
}
```

## Parsed Skill Queries (JSON)

```json
{
  "web_search": [
    "incorrect inductive biases in deep learning vision domain",
    "language models shortcut learning examples",
    "mitigating inductive biases in AI training",
    "novel methods for addressing deep learning biases"
  ],
  "academic_search": [
    "definition of inductive bias in machine learning",
    "experiments on incorrect generalizations in neural networks",
    "cross-domain failures of inductive biases",
    "adversarial training for bias mitigation in deep learning"
  ],
  "dataset_search": [
    "datasets for fruit classification with background variations",
    "text datasets with spurious correlations for language models",
    "unbiased test sets for deep learning bias evaluation",
    "augmented datasets for inductive bias correction"
  ],
  "video_search": [
    "inductive biases in deep learning talks",
    "examples of bias in vision AI experiments",
    "tutorials on detecting inductive biases in models",
    "methods to mitigate AI biases in practice"
  ]
}
```

