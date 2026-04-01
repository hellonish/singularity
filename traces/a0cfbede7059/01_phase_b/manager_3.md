# Manager 3 — Report Structure Proposal

## System Prompt

# REPORT MANAGER

You are one of three independent Report Managers. Each manager is assigned a
**different structural perspective**. You must follow your assigned perspective
rigorously — it is what makes your proposal uniquely valuable to the Lead.

## Your Role

You think like a senior editor at a world-class research publication. You receive:
- A research query
- A target section count N (pre-rolled — you must hit this exactly)
- A list of available retrieval skills (these will run after your plan is finalised,
  fetching evidence targeted at the sections you define — design sections that make
  full use of these evidence types)
- A `structural_perspective` label and `perspective_instruction` — **this is your
  mandatory organising principle. Your chapter order, chapter titles, and the
  progression from section to section must all reflect this perspective.**
- An `audience` label — **this determines technical depth and structural complexity**

## Perspective Compliance

- Read `perspective_instruction` carefully before designing any node.
- Your chapter sequence must visibly follow the perspective's logic.
- Sections within each chapter must reinforce the perspective — not drift toward
  whatever the "obvious" structure would be.
- If your tree looks like a generic textbook outline, you have not followed your
  perspective. Revise before emitting.

## Audience Adaptation

Match structural complexity and section depth to the stated audience:

**layperson**
- Prefer narrative chapter flow over taxonomy
- Lead with concrete examples before abstract concepts
- Avoid subsections inside subsections — max 2 levels below root
- Each section description should mention what everyday analogy or example it uses

**practitioner**
- Balance theory and application — neither should dominate
- Include implementation, edge cases, and validation chapters explicitly
- Subsections are appropriate where genuine step-level detail exists
- Sections can assume domain vocabulary without definition

**expert**
- Maximise density: subsections are preferred over long undifferentiated sections
- Lead with what is novel or non-obvious; skip motivation that experts already know
- Mathematical formalism should have its own dedicated sections, not be buried
- Section descriptions should name specific theorems, algorithms, or datasets

**student**
- Begin with motivation before formalism
- Explicit worked-example sections are required, not optional
- Progress from simple to complex within each chapter
- Include a "common mistakes" or "misconceptions" section where relevant

## Depth Principles

Use these content-driven rules instead of rigid counts:

1. **Add a chapter** when a coherent body of argument or evidence stands independently
   from siblings. Chapters should not be collections of unrelated sections.
2. **Add a section under a chapter** when it covers a distinct subtopic with its own
   evidence, not just a paragraph-length elaboration of the parent.
3. **Add a subsection** only when the section contains genuinely separable sub-arguments
   with different evidence types, or when the audience (expert/student) benefits from
   explicit granularity. Do not use subsections as padding.
4. **Do not add depth to reach a node count target.** If you are short on nodes,
   expand chapters with additional peer sections — never create depth for its own sake.
5. **Sibling sections must be genuinely parallel** — same level of abstraction, same
   evidence type, same rhetorical role. A section that is really a paragraph belongs
   inside its parent, not as a peer.

## Tree Rules

1. Every node has: node_id, parent_id (null for root), level, title, description,
   section_type (root | chapter | section | subsection)
2. Root: exactly 1 node at level 0
3. Chapters: 3–7 nodes at level 1 — fewer if the topic does not warrant more
4. Sections: 2–6 nodes per chapter — determined by content, not by filling the range
5. Subsections: level 3 nodes — use when content-driven depth principles above require it
6. No node may be left as a stub — every description must explain what evidence
   or argument this section will present, and which retrieval skills will provide it
7. The tree must be coherent: a reader following the hierarchy should get a
   complete, well-structured report

## Quality Axes

Coverage, logical flow through your chosen perspective, no redundancy between
sibling sections, appropriate depth for the audience, clear intellectual progression
that a reader can follow from the opening chapter to the last.

## Output — respond ONLY with this JSON, no prose

```json
{
  "proposal_id": "manager_N",
  "total_nodes": 0,
  "rationale": "One sentence: the organising principle of this structure",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "...",
      "description": "What this root section covers and how it frames the whole report",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "...",
      "description": "What evidence and argument this chapter presents",
      "section_type": "chapter"
    }
  ]
}
```

CRITICAL: Count every object in the `tree` array. `total_nodes` must equal that count.
If your count does not match the target N given in the input, fix it before responding.


## User Message

query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method. Report Describing your Approach for Realizing the Project
strength_context: target_section_count=28
available_retrieval_skills: financial_search, gov_search, code_search, book_search, web_search, dataset_search, data_extraction, forum_search, video_search, multimedia_search, standards_search, patent_search, legal_search, academic_search, clinical_search, pdf_deep_extract, social_search, news_archive
audience: practitioner
proposal_id: manager_3
structural_perspective: practitioner-workflow
perspective_instruction:
ROLE: You are a practitioner's guide architect. Your structure answers the questions a working engineer or analyst actually asks: when do I use this, how do I use it, what breaks, and how do I verify it worked.

STRUCTURE PRINCIPLE: Organise as a practitioner's guide: when and why to use this technique, step-by-step implementation with decision points, common edge cases and failure modes, validation strategies, and performance/complexity considerations. Theory appears only where it directly informs a decision.

KEY QUESTIONS — your tree must answer these:
  - What decision gate tells a practitioner when to reach for this technique vs. an alternative?
  - What are the top-3 failure modes, and how does the practitioner detect and recover from each?
  - What does 'done correctly' look like — what can be measured, tested, or audited?

ANTI-PATTERNS — explicitly avoid:
  ✗ Do NOT lead with history or theory — lead with a decision ('When to use this').
  ✗ Do NOT write a section that is pure background with no actionable guidance.
  ✗ Do NOT treat validation as a footnote — it should be a first-class chapter.

Produce exactly 28 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_3",
  "total_nodes": 28,
  "rationale": "This structure organizes the report as a practitioner's workflow, guiding engineers through decision-making, implementation, failure handling, validation, and optimization for managing incorrect inductive biases in deep learning.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Practitioner's Guide to Handling Incorrect Inductive Biases in Deep Learning",
      "description": "This root frames the report as a workflow for practitioners, covering when to intervene in inductive biases, how to implement fixes, handle failures, validate outcomes, and optimize performance, using evidence from academic_search, dataset_search, and video_search to inform actionable steps.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "When and Why to Address Inductive Biases",
      "description": "Outlines decision gates for practitioners to identify when inductive biases lead to model failures, such as in vision or language tasks, using academic_search for comparative studies and web_search for real-world case examples to decide between bias mitigation and alternative techniques.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Decision Gates for Bias Detection",
      "description": "Explains how to evaluate if a bias like background color confounding in fruit classification is present, using dataset_search to fetch experimental datasets and code_search for diagnostic tools to compare against alternatives like ensemble methods.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Why Choose Bias Mitigation Over Alternatives",
      "description": "Discusses scenarios where addressing biases outperforms simpler models, drawing from forum_search for practitioner experiences and academic_search for benchmarks to inform decisions on cost vs. benefit.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n2",
      "level": 2,
      "title": "Top Triggers in Different Domains",
      "description": "Covers domain-specific signals like spurious correlations in vision vs. language, using video_search from the provided talk and dataset_search for experiments to guide when to prioritize bias fixes.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "Step-by-Step Implementation of Bias Handling",
      "description": "Provides a sequential guide for implementing techniques to correct inductive biases, including data augmentation and regularization, with code_search for scripts and dataset_search for illustrative experiments.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n6",
      "level": 2,
      "title": "Initial Data Preparation and Augmentation",
      "description": "Details steps to preprocess datasets to reduce biases, such as varying backgrounds in image tasks, using dataset_search for augmented samples and code_search for implementation code with decision points for tool selection.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n6",
      "level": 2,
      "title": "Model Selection and Training Adjustments",
      "description": "Guides on choosing architectures that minimize biases, like adding adversarial training, with academic_search for relevant papers and code_search for step-by-step code snippets including hyperparameter decisions.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n6",
      "level": 2,
      "title": "Integration with Existing Workflows",
      "description": "Explains how to incorporate bias handling into standard pipelines, using web_search for real-world examples and patent_search for innovative methods, with checkpoints for verifying integration success.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n6",
      "level": 2,
      "title": "Testing Implementation Decisions",
      "description": "Outlines decision trees for selecting between techniques based on project constraints, supported by dataset_search for validation experiments.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n6",
      "level": 2,
      "title": "Substep: Handling Domain-Specific Variations",
      "description": "Breaks down adaptations for vision vs. language, such as using multimedia_search for visual examples, as a subsection to testing.",
      "section_type": "subsection"
    },
    {
      "node_id": "n12",
      "parent_id": "n1",
      "level": 1,
      "title": "Identifying and Handling Failure Modes",
      "description": "Addresses the top-3 failure modes of inductive biases, like overfitting to confounders, and recovery strategies, using academic_search for case studies and forum_search for detection tips.",
      "section_type": "chapter"
    },
    {
      "node_id": "n13",
      "parent_id": "n12",
      "level": 2,
      "title": "Failure Mode 1: Spurious Correlations",
      "description": "Describes detection and recovery from biases like background color in classification, with dataset_search for experiments and code_search for diagnostic tests.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n12",
      "level": 2,
      "title": "Failure Mode 2: Domain Shift Issues",
      "description": "Covers how biases fail across domains, with strategies to detect via cross-validation, using video_search for illustrations and academic_search for recovery methods.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n12",
      "level": 2,
      "title": "Failure Mode 3: Overgeneralization",
      "description": "Explains detection of models learning incorrect patterns and recovery steps, supported by news_archive for real-world failures and dataset_search for corrective experiments.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n12",
      "level": 2,
      "title": "General Recovery Strategies",
      "description": "Provides overarching tactics for all modes, like retraining, using code_search for tools.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n1",
      "level": 1,
      "title": "Validation and Verification Strategies",
      "description": "Details how to measure and audit successful bias handling, ensuring 'done correctly' through metrics and tests, with academic_search for standards and dataset_search for validation data.",
      "section_type": "chapter"
    },
    {
      "node_id": "n18",
      "parent_id": "n17",
      "level": 2,
      "title": "Key Metrics for Success",
      "description": "Defines measurable outcomes like accuracy on unbiased test sets, using dataset_search for benchmarks and standards_search for evaluation protocols.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n17",
      "level": 2,
      "title": "Auditing Techniques",
      "description": "Guides on verifying bias absence through sensitivity analysis, with code_search for auditing scripts and academic_search for methods.",
      "section_type": "section"
    },
    {
      "node_id": "n20",
      "parent_id": "n17",
      "level": 2,
      "title": "Cross-Validation Approaches",
      "description": "Explains decision points for choosing validation methods, supported by book_search for best practices and dataset_search for examples.",
      "section_type": "section"
    },
    {
      "node_id": "n21",
      "parent_id": "n17",
      "level": 2,
      "title": "Subsection: Automated Verification Tools",
      "description": "Details specific tools for automated checks, as a subsection to auditing.",
      "section_type": "subsection"
    },
    {
      "node_id": "n22",
      "parent_id": "n1",
      "level": 1,
      "title": "Solutions from Literature and Custom Methods",
      "description": "Reviews literature-based solutions and proposes a custom approach for addressing biases, with academic_search for papers and original analysis for practitioner adaptation.",
      "section_type": "chapter"
    },
    {
      "node_id": "n23",
      "parent_id": "n22",
      "level": 2,
      "title": "Literature Solution 1: Data Augmentation Techniques",
      "description": "Implements methods from key papers, using academic_search for references and dataset_search for application examples.",
      "section_type": "section"
    },
    {
      "node_id": "n24",
      "parent_id": "n22",
      "level": 2,
      "title": "Literature Solution 2: Adversarial Training",
      "description": "Details step-by-step use of adversarial methods, with code_search for implementations and video_search for explanations.",
      "section_type": "section"
    },
    {
      "node_id": "n25",
      "parent_id": "n22",
      "level": 2,
      "title": "Custom Method Proposal",
      "description": "Suggests a novel hybrid approach, drawing from patent_search for inspiration and dataset_search for testing.",
      "section_type": "section"
    },
    {
      "node_id": "n26",
      "parent_id": "n22",
      "level": 2,
      "title": "Decision Points for Solution Selection",
      "description": "Guides choosing between solutions based on project needs, using web_search for comparisons.",
      "section_type": "section"
    },
    {
      "node_id": "n27",
      "parent_id": "n1",
      "level": 1,
      "title": "Performance Optimization and Best Practices",
      "description": "Covers complexity trade-offs and optimization strategies for bias handling, with standards_search for guidelines and academic_search for performance data.",
      "section_type": "chapter"
    },
    {
      "node_id": "n28",
      "parent_id": "n27",
      "level": 2,
      "title": "Balancing Accuracy and Efficiency",
      "description": "Explains how to optimize for computational resources while maintaining bias correction, using code_search for efficient implementations and dataset_search for benchmarks.",
      "section_type": "section"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_3",
  "rationale": "This structure organizes the report as a practitioner's workflow, guiding engineers through decision-making, implementation, failure handling, validation, and optimization for managing incorrect inductive biases in deep learning.",
  "total_nodes": 28,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Practitioner's Guide to Handling Incorrect Inductive Biases in Deep Learning",
      "description": "This root frames the report as a workflow for practitioners, covering when to intervene in inductive biases, how to implement fixes, handle failures, validate outcomes, and optimize performance, using evidence from academic_search, dataset_search, and video_search to inform actionable steps.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "When and Why to Address Inductive Biases",
      "description": "Outlines decision gates for practitioners to identify when inductive biases lead to model failures, such as in vision or language tasks, using academic_search for comparative studies and web_search for real-world case examples to decide between bias mitigation and alternative techniques.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Decision Gates for Bias Detection",
      "description": "Explains how to evaluate if a bias like background color confounding in fruit classification is present, using dataset_search to fetch experimental datasets and code_search for diagnostic tools to compare against alternatives like ensemble methods.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Why Choose Bias Mitigation Over Alternatives",
      "description": "Discusses scenarios where addressing biases outperforms simpler models, drawing from forum_search for practitioner experiences and academic_search for benchmarks to inform decisions on cost vs. benefit.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n2",
      "level": 2,
      "title": "Top Triggers in Different Domains",
      "description": "Covers domain-specific signals like spurious correlations in vision vs. language, using video_search from the provided talk and dataset_search for experiments to guide when to prioritize bias fixes.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "Step-by-Step Implementation of Bias Handling",
      "description": "Provides a sequential guide for implementing techniques to correct inductive biases, including data augmentation and regularization, with code_search for scripts and dataset_search for illustrative experiments.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n6",
      "level": 2,
      "title": "Initial Data Preparation and Augmentation",
      "description": "Details steps to preprocess datasets to reduce biases, such as varying backgrounds in image tasks, using dataset_search for augmented samples and code_search for implementation code with decision points for tool selection.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n6",
      "level": 2,
      "title": "Model Selection and Training Adjustments",
      "description": "Guides on choosing architectures that minimize biases, like adding adversarial training, with academic_search for relevant papers and code_search for step-by-step code snippets including hyperparameter decisions.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n6",
      "level": 2,
      "title": "Integration with Existing Workflows",
      "description": "Explains how to incorporate bias handling into standard pipelines, using web_search for real-world examples and patent_search for innovative methods, with checkpoints for verifying integration success.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n6",
      "level": 2,
      "title": "Testing Implementation Decisions",
      "description": "Outlines decision trees for selecting between techniques based on project constraints, supported by dataset_search for validation experiments.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n6",
      "level": 2,
      "title": "Substep: Handling Domain-Specific Variations",
      "description": "Breaks down adaptations for vision vs. language, such as using multimedia_search for visual examples, as a subsection to testing.",
      "section_type": "subsection"
    },
    {
      "node_id": "n12",
      "parent_id": "n1",
      "level": 1,
      "title": "Identifying and Handling Failure Modes",
      "description": "Addresses the top-3 failure modes of inductive biases, like overfitting to confounders, and recovery strategies, using academic_search for case studies and forum_search for detection tips.",
      "section_type": "chapter"
    },
    {
      "node_id": "n13",
      "parent_id": "n12",
      "level": 2,
      "title": "Failure Mode 1: Spurious Correlations",
      "description": "Describes detection and recovery from biases like background color in classification, with dataset_search for experiments and code_search for diagnostic tests.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n12",
      "level": 2,
      "title": "Failure Mode 2: Domain Shift Issues",
      "description": "Covers how biases fail across domains, with strategies to detect via cross-validation, using video_search for illustrations and academic_search for recovery methods.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n12",
      "level": 2,
      "title": "Failure Mode 3: Overgeneralization",
      "description": "Explains detection of models learning incorrect patterns and recovery steps, supported by news_archive for real-world failures and dataset_search for corrective experiments.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n12",
      "level": 2,
      "title": "General Recovery Strategies",
      "description": "Provides overarching tactics for all modes, like retraining, using code_search for tools.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n1",
      "level": 1,
      "title": "Validation and Verification Strategies",
      "description": "Details how to measure and audit successful bias handling, ensuring 'done correctly' through metrics and tests, with academic_search for standards and dataset_search for validation data.",
      "section_type": "chapter"
    },
    {
      "node_id": "n18",
      "parent_id": "n17",
      "level": 2,
      "title": "Key Metrics for Success",
      "description": "Defines measurable outcomes like accuracy on unbiased test sets, using dataset_search for benchmarks and standards_search for evaluation protocols.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n17",
      "level": 2,
      "title": "Auditing Techniques",
      "description": "Guides on verifying bias absence through sensitivity analysis, with code_search for auditing scripts and academic_search for methods.",
      "section_type": "section"
    },
    {
      "node_id": "n20",
      "parent_id": "n17",
      "level": 2,
      "title": "Cross-Validation Approaches",
      "description": "Explains decision points for choosing validation methods, supported by book_search for best practices and dataset_search for examples.",
      "section_type": "section"
    },
    {
      "node_id": "n21",
      "parent_id": "n17",
      "level": 2,
      "title": "Subsection: Automated Verification Tools",
      "description": "Details specific tools for automated checks, as a subsection to auditing.",
      "section_type": "subsection"
    },
    {
      "node_id": "n22",
      "parent_id": "n1",
      "level": 1,
      "title": "Solutions from Literature and Custom Methods",
      "description": "Reviews literature-based solutions and proposes a custom approach for addressing biases, with academic_search for papers and original analysis for practitioner adaptation.",
      "section_type": "chapter"
    },
    {
      "node_id": "n23",
      "parent_id": "n22",
      "level": 2,
      "title": "Literature Solution 1: Data Augmentation Techniques",
      "description": "Implements methods from key papers, using academic_search for references and dataset_search for application examples.",
      "section_type": "section"
    },
    {
      "node_id": "n24",
      "parent_id": "n22",
      "level": 2,
      "title": "Literature Solution 2: Adversarial Training",
      "description": "Details step-by-step use of adversarial methods, with code_search for implementations and video_search for explanations.",
      "section_type": "section"
    },
    {
      "node_id": "n25",
      "parent_id": "n22",
      "level": 2,
      "title": "Custom Method Proposal",
      "description": "Suggests a novel hybrid approach, drawing from patent_search for inspiration and dataset_search for testing.",
      "section_type": "section"
    },
    {
      "node_id": "n26",
      "parent_id": "n22",
      "level": 2,
      "title": "Decision Points for Solution Selection",
      "description": "Guides choosing between solutions based on project needs, using web_search for comparisons.",
      "section_type": "section"
    },
    {
      "node_id": "n27",
      "parent_id": "n1",
      "level": 1,
      "title": "Performance Optimization and Best Practices",
      "description": "Covers complexity trade-offs and optimization strategies for bias handling, with standards_search for guidelines and academic_search for performance data.",
      "section_type": "chapter"
    },
    {
      "node_id": "n28",
      "parent_id": "n27",
      "level": 2,
      "title": "Balancing Accuracy and Efficiency",
      "description": "Explains how to optimize for computational resources while maintaining bias correction, using code_search for efficient implementations and dataset_search for benchmarks.",
      "section_type": "section"
    }
  ]
}
```

