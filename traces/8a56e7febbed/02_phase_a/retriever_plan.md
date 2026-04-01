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
research_query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method.
report_sections (25 planned, 18 leaf sections):
  - [n1] Understanding and Mitigating Incorrect Inductive Biases in Deep Learning: This report provides a comprehensive guide to incorrect inductive biases in deep
  - [n2] Foundations of Inductive Biases: Introduces the core concepts and definitions of inductive biases, focusing on wh
  - [n3] Core Definitions and Principles: Defines inductive biases and distinguishes between correct and incorrect biases,
  - [n4] Mechanisms Behind Incorrect Biases: Explores the mechanisms in neural networks that lead to incorrect biases, such a
  - [n5] Illustrating Incorrect Biases with Examples: Presents real-world examples of incorrect inductive biases across domains, focus
  - [n6] Background Color Bias in Vision Models: Details the fruit classification problem where models learn background colors in
  - [n7] Positional Bias in Language Models: Examines how language models over-rely on word positions rather than semantic co
  - [n8] Cross-Domain Bias Challenges: Discusses how biases manifest and interact across vision and language domains, h
  - [n9] Experimental Validation of Biases: Outlines experiments to replicate and measure the impact of incorrect inductive 
  - [n10] Replicating the Fruit Classification Experiment: Provides a step-by-step guide to replicate the background color bias experiment 
  - [n11] Testing Positional Bias in Language Tasks: Describes experimental setups to expose positional biases in NLP models, with me
  - [n12] Measuring Impact on Model Performance: Details methods to measure how biases affect real-world model performance, using
  - [n13] Strategies to Address Incorrect Biases: Explores established and innovative methods to mitigate incorrect inductive bias
  - [n14] Data Augmentation Techniques: Reviews data augmentation as a method to counter biases by diversifying training
  - [n15] Regularization Methods: Discusses regularization techniques to prevent overfitting to spurious features,
  - [n16] Adversarial Training Approaches: Explores adversarial training to expose and correct biases, with case studies fr
  - [n17] Proposed Hybrid Bias Reduction Method: Suggests a novel approach combining data mixing and adversarial training to addr
  - [n18] Implementing and Validating Mitigation Strategies: Guides practitioners through the workflow of implementing bias mitigation techni
  - [n19] Step-by-Step Implementation for Vision Tasks: Details implementation steps for bias mitigation in vision models, focusing on d
  - [n20] Step-by-Step Implementation for Language Tasks: Outlines implementation of mitigation strategies for language models, addressing
  - [n21] Handling Failure Modes: Identifies common failure modes in bias mitigation and provides recovery strateg
  - [n22] Validation Metrics and Protocols: Explains metrics and protocols to validate the effectiveness of bias mitigation,
  - [n23] Performance and Scalability Considerations: Evaluates the trade-offs and scalability of bias mitigation techniques in produc
  - [n24] Complexity and Resource Trade-Offs: Analyzes the computational costs and resource demands of implementing bias mitig
  - [n25] Integration into ML Pipelines: Discusses how to integrate bias mitigation into existing machine learning workfl

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
    "selected": ["academic_search", "dataset_search", "video_search"],
    "reasoning": {
      "academic_search": "To retrieve peer-reviewed papers on inductive biases in deep learning for theoretical and experimental analysis.",
      "dataset_search": "To find relevant datasets for validating experiments on biases in various domains like vision and language.",
      "video_search": "To source educational videos that illustrate concepts and experiments on inductive biases."
    }
  },
  "skill_queries": {
    "web_search": [
      {"query": "inductive biases in deep learning", "for_sections": ["n2", "n3"]},
      {"query": "incorrect inductive biases in computer vision", "for_sections": ["n5", "n6"]},
      {"query": "positional bias experiments in language models", "for_sections": ["n9", "n11"]},
      {"query": "mitigating inductive biases in AI models", "for_sections": ["n13", "n14"]}
    ],
    "academic_search": [
      {"query": "inductive biases neural networks", "for_sections": ["n3", "n4"]},
      {"query": "background color bias vision models", "for_sections": ["n6", "n10"]},
      {"query": "positional encoding biases NLP", "for_sections": ["n7", "n11"]},
      {"query": "bias mitigation techniques machine learning", "for_sections": ["n13", "n16"]}
    ],
    "dataset_search": [
      {"query": "fruit classification datasets computer vision", "for_sections": ["n6", "n10"]},
      {"query": "NLP datasets with positional features", "for_sections": ["n7", "n11"]},
      {"query": "benchmarks for deep learning biases", "for_sections": ["n9", "n12"]},
      {"query": "diverse datasets for AI bias reduction", "for_sections": ["n14", "n19"]}
    ],
    "video_search": [
      {"query": "inductive biases machine learning tutorials", "for_sections": ["n2", "n3"]},
      {"query": "deep learning biases in vision examples", "for_sections": ["n5", "n10"]},
      {"query": "language model positional bias lectures", "for_sections": ["n7", "n11"]},
      {"query": "adversarial training for AI biases", "for_sections": ["n13", "n18"]}
    ]
  }
}
```

## Parsed Skill Queries (JSON)

```json
{
  "web_search": [
    "inductive biases in deep learning",
    "incorrect inductive biases in computer vision",
    "positional bias experiments in language models",
    "mitigating inductive biases in AI models"
  ],
  "academic_search": [
    "inductive biases neural networks",
    "background color bias vision models",
    "positional encoding biases NLP",
    "bias mitigation techniques machine learning"
  ],
  "dataset_search": [
    "fruit classification datasets computer vision",
    "NLP datasets with positional features",
    "benchmarks for deep learning biases",
    "diverse datasets for AI bias reduction"
  ],
  "video_search": [
    "inductive biases machine learning tutorials",
    "deep learning biases in vision examples",
    "language model positional bias lectures",
    "adversarial training for AI biases"
  ]
}
```

