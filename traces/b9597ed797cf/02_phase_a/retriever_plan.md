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

report_sections (22 planned, 14 leaf sections):
  - [n1] Navigating Incorrect Inductive Biases in Deep Learning: A Practitioner’s Guide: This report provides a comprehensive journey from understanding incorrect induct
  - [n2] Understanding Inductive Biases: Foundations: Introduces the core concepts and theoretical underpinnings of inductive biases, 
  - [n3] Definitions and Key Concepts: Outlines essential terms like inductive bias and generalization, drawing on foun
  - [n4] Mathematical Formalism of Biases: Presents mathematical models of inductive biases, using academic papers to highl
  - [n5] Real-World Problem: The Apple-Orange Background Bias: Introduces a concrete example where a model incorrectly learns to classify fruit
  - [n6] Experiment Setup and Execution: Details the setup of the apple-orange classification task with biased background
  - [n7] Analyzing Model Failure: Examines how background bias leads to poor generalization, using training logs a
  - [n8] Incorrect Biases in Vision Domains: Explores additional vision-specific biases like texture over shape, building on 
  - [n9] Texture vs. Shape Bias Experiment: Conducts experiments showing models prioritizing textures over shapes, using ima
  - [n10] Implications for Vision Tasks: Discusses broader implications of vision biases, including adversarial examples,
  - [n11] Incorrect Biases in Language Domains: Addresses language-specific biases such as positional overfitting in NLP, extend
  - [n12] Positional Bias in Text Classification: Illustrates experiments where models overfit to word positions in text, using NL
  - [n13] Challenges with Sequence Learning: Explores additional language biases like out-of-vocabulary issues, using real-wo
  - [n14] Common Failure Modes Across Domains: Identifies key failure modes of incorrect inductive biases in deep learning, foc
  - [n15] Background Dominance in Vision: Details detection of biases like color-based classification and initial recovery
  - [n16] Domain Shifts in Language: Explains how to identify shifts in language data and initial mitigation approach
  - [n17] Step-by-Step Implementation of Bias Mitigation: Provides actionable steps for practitioners to implement experiments and address
  - [n18] Setting Up Bias Experiments: Guides on creating datasets and models to test biases, using synthetic data and 
  - [n19] Training and Iterative Adjustment: Outlines training decisions and iterative testing to counter biases, with exampl
  - [n20] Solutions and Validation for Bias Mitigation: Reviews established solutions from literature, proposes a novel method, and outl
  - [n21] Literature-Based Solutions: Discusses solutions like data augmentation and regularization, drawing on academ
  - [n22] Proposed Method and Validation: Suggests a new practitioner-oriented method for bias mitigation, with validation

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
      "web_search": "Fits for gathering general information on inductive biases in deep learning, as the query involves broad concepts and examples.",
      "academic_search": "Relevant for retrieving scholarly papers on incorrect inductive biases, experiments, and solutions in ML research.",
      "dataset_search": "Appropriate for finding datasets used in vision and language experiments to illustrate biases, aligning with the report's experimental sections.",
      "video_search": "Useful for accessing talks and videos on inductive biases, such as the referenced YouTube link, to support educational and illustrative content."
    }
  },
  "skill_queries": {
    "web_search": [
      {"query": "inductive biases in deep learning", "for_sections": ["n2", "n3"]},
      {"query": "examples of incorrect inductive biases in vision models", "for_sections": ["n8", "n9"]},
      {"query": "positional overfitting in NLP", "for_sections": ["n11", "n12"]},
      {"query": "mitigating inductive biases in machine learning", "for_sections": ["n20", "n21"]}
    ],
    "academic_search": [
      {"query": "theoretical foundations of inductive biases", "for_sections": ["n3", "n4"]},
      {"query": "experiments on texture bias in computer vision", "for_sections": ["n9", "n10"]},
      {"query": "language model biases in sequence learning", "for_sections": ["n13", "n14"]},
      {"query": "solutions for addressing inductive biases in deep learning", "for_sections": ["n21", "n22"]}
    ],
    "dataset_search": [
      {"query": "datasets for fruit classification tasks", "for_sections": ["n5", "n6"]},
      {"query": "vision datasets with shape and texture variations", "for_sections": ["n9", "n15"]},
      {"query": "NLP datasets for positional bias analysis", "for_sections": ["n12", "n16"]},
      {"query": "synthetic datasets for bias mitigation experiments", "for_sections": ["n18", "n19"]}
    ],
    "video_search": [
      {"query": "lectures on inductive biases in AI", "for_sections": ["n2", "n3"]},
      {"query": "demonstrations of vision model failures due to biases", "for_sections": ["n8", "n9"]},
      {"query": "talks on language model overfitting issues", "for_sections": ["n11", "n13"]},
      {"query": "tutorials on fixing inductive biases in deep learning", "for_sections": ["n20", "n22"]}
    ]
  }
}
```

## Parsed Skill Queries (JSON)

```json
{
  "web_search": [
    "inductive biases in deep learning",
    "examples of incorrect inductive biases in vision models",
    "positional overfitting in NLP",
    "mitigating inductive biases in machine learning"
  ],
  "academic_search": [
    "theoretical foundations of inductive biases",
    "experiments on texture bias in computer vision",
    "language model biases in sequence learning",
    "solutions for addressing inductive biases in deep learning"
  ],
  "dataset_search": [
    "datasets for fruit classification tasks",
    "vision datasets with shape and texture variations",
    "NLP datasets for positional bias analysis",
    "synthetic datasets for bias mitigation experiments"
  ],
  "video_search": [
    "lectures on inductive biases in AI",
    "demonstrations of vision model failures due to biases",
    "talks on language model overfitting issues",
    "tutorials on fixing inductive biases in deep learning"
  ]
}
```

