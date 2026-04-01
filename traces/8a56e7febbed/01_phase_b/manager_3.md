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

query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method.
strength_context: target_section_count=29
available_retrieval_skills: dataset_search, book_search, patent_search, data_extraction, pdf_deep_extract, clinical_search, standards_search, legal_search, news_archive, forum_search, code_search, financial_search, multimedia_search, gov_search, video_search, academic_search, web_search, social_search
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

Produce exactly 29 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_3",
  "total_nodes": 29,
  "rationale": "This structure follows a practitioner's workflow by sequencing decisions, implementations, failure handling, validation, and performance to guide engineers on practical application of bias mitigation.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Practitioner's Guide to Mitigating Incorrect Inductive Biases in Deep Learning",
      "description": "This root frames the report as a step-by-step workflow for engineers to identify, implement, and verify strategies against inductive biases that cause poor generalization, drawing on academic_search and dataset_search for real-world experiments.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Deciding When to Address Inductive Biases",
      "description": "Outlines decision gates for practitioners to choose bias mitigation over alternatives, using academic_search to compare techniques based on project constraints like dataset size and domain.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Key Decision Gates for Technique Selection",
      "description": "Covers criteria like generalization gaps in initial tests to decide when to apply bias fixes versus standard training, with dataset_search providing examples from vision tasks.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "When to Choose Bias Mitigation Over Alternatives",
      "description": "Explains scenarios where biases like background color shortcuts in image classification outweigh benefits of simpler models, using web_search for case studies on trade-offs.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n2",
      "level": 2,
      "title": "Top Use Cases in Different Domains",
      "description": "Details domain-specific triggers, such as language model shortcuts in text classification, with academic_search retrieving experiments to inform when to intervene.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n2",
      "level": 2,
      "title": "Why Addressing Biases Improves Outcomes",
      "description": "Links decisions to measurable outcomes like accuracy drops in new environments, using dataset_search for quick benchmarks to guide practitioner choices.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n1",
      "level": 1,
      "title": "Implementing Mitigation Techniques",
      "description": "Provides step-by-step implementation for addressing incorrect biases, including code snippets and tools, with code_search and academic_search for verified methods.",
      "section_type": "chapter"
    },
    {
      "node_id": "n8",
      "parent_id": "n7",
      "level": 2,
      "title": "Step-by-Step for Vision Domain Biases",
      "description": "Guides on implementing data augmentation to counter background biases, using dataset_search for experiment setups and code_search for library integrations.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n7",
      "level": 2,
      "title": "Step-by-Step for Language Domain Biases",
      "description": "Outlines techniques like adversarial training for shortcut learning, with academic_search providing literature on decision points for parameter tuning.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n7",
      "level": 2,
      "title": "Tools and Libraries for Implementation",
      "description": "Recommends frameworks like TensorFlow for bias detection, including decision points for customization, with code_search for ready-to-use scripts.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n7",
      "level": 2,
      "title": "Handling Decision Points in Workflow",
      "description": "Covers branching choices, such as when to add regularization, using dataset_search for A/B test evidence to validate implementation paths.",
      "section_type": "section"
    },
    {
      "node_id": "n12",
      "parent_id": "n7",
      "level": 2,
      "title": "Integrating with Existing Pipelines",
      "description": "Explains how to insert bias checks into ML pipelines, with web_search for real-world examples of seamless integration decisions.",
      "section_type": "section"
    },
    {
      "node_id": "n13",
      "parent_id": "n1",
      "level": 1,
      "title": "Handling Edge Cases and Failure Modes",
      "description": "Identifies top failure modes of bias mitigation and recovery strategies, using dataset_search for detection experiments in various domains.",
      "section_type": "chapter"
    },
    {
      "node_id": "n14",
      "parent_id": "n13",
      "level": 2,
      "title": "Top-Three Failure Modes in Practice",
      "description": "Details modes like overfitting to spurious correlations, with academic_search providing experiments to help practitioners detect them early.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n13",
      "level": 2,
      "title": "Detecting Failure Modes in Vision Tasks",
      "description": "Outlines diagnostic tests for biases, such as cross-domain validation, using dataset_search for edge case datasets.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n13",
      "level": 2,
      "title": "Detecting Failure Modes in Language Tasks",
      "description": "Covers tools for spotting biases in text data, with forum_search for practitioner-reported issues and recovery tactics.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n13",
      "level": 2,
      "title": "Recovery Strategies for Each Mode",
      "description": "Provides actionable steps to fix detected failures, like retraining with balanced data, using academic_search for evidence-based methods.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n13",
      "level": 2,
      "title": "Edge Cases in Multi-Domain Applications",
      "description": "Addresses combined domain failures, with dataset_search for experiments illustrating decision points for escalation.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n1",
      "level": 1,
      "title": "Validating Bias Mitigation",
      "description": "Focuses on strategies to measure and audit successful bias handling, using academic_search and dataset_search for validation benchmarks.",
      "section_type": "chapter"
    },
    {
      "node_id": "n20",
      "parent_id": "n19",
      "level": 2,
      "title": "Measurement Techniques for Effectiveness",
      "description": "Explains metrics like out-of-distribution accuracy to verify mitigation, with dataset_search providing test sets for practical auditing.",
      "section_type": "section"
    },
    {
      "node_id": "n21",
      "parent_id": "n19",
      "level": 2,
      "title": "Auditing Protocols for Biases",
      "description": "Guides on systematic reviews of model decisions, using web_search for tools that flag potential issues in real-time.",
      "section_type": "section"
    },
    {
      "node_id": "n22",
      "parent_id": "n19",
      "level": 2,
      "title": "Testing Against Known Biases",
      "description": "Outlines experiments to simulate biases and confirm fixes, with academic_search for literature on validation setups.",
      "section_type": "section"
    },
    {
      "node_id": "n23",
      "parent_id": "n19",
      "level": 2,
      "title": "What 'Done Correctly' Looks Like",
      "description": "Defines success through testable outcomes, like consistent performance across environments, using dataset_search for benchmarks.",
      "section_type": "section"
    },
    {
      "node_id": "n24",
      "parent_id": "n19",
      "level": 2,
      "title": "Iterative Validation Workflows",
      "description": "Describes loops for ongoing checks, with forum_search for practitioner tips on integrating validation decisions.",
      "section_type": "section"
    },
    {
      "node_id": "n25",
      "parent_id": "n1",
      "level": 1,
      "title": "Performance Considerations and Advanced Topics",
      "description": "Evaluates trade-offs in mitigation techniques, using academic_search for complexity analysis to inform scaling decisions.",
      "section_type": "chapter"
    },
    {
      "node_id": "n26",
      "parent_id": "n25",
      "level": 2,
      "title": "Complexity and Resource Trade-Offs",
      "description": "Analyzes computational costs of bias fixes, with code_search for optimized implementations to guide practitioner choices.",
      "section_type": "section"
    },
    {
      "node_id": "n27",
      "parent_id": "n25",
      "level": 2,
      "title": "Scalability in Production Environments",
      "description": "Discusses adapting techniques for large-scale use, using dataset_search for evidence on performance under constraints.",
      "section_type": "section"
    },
    {
      "node_id": "n28",
      "parent_id": "n25",
      "level": 2,
      "title": "Suggested Solutions from Literature",
      "description": "Reviews methods like debiasing algorithms, with academic_search for experiments and decision points for adoption.",
      "section_type": "section"
    },
    {
      "node_id": "n29",
      "parent_id": "n25",
      "level": 2,
      "title": "Custom Practitioner Methods for Bias Addressing",
      "description": "Proposes novel approaches, such as hybrid data sampling, with web_search for validation ideas tailored to real-world workflows.",
      "section_type": "section"
    },
    {
      "node_id": "n30",
      "parent_id": "n25",
      "level": 2,
      "title": "Integration with Overall ML Strategy",
      "description": "Explains how to weave bias mitigation into broader strategies, using forum_search for practical performance insights.",
      "section_type": "section"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_3",
  "rationale": "This structure follows a practitioner's workflow by sequencing decisions, implementations, failure handling, validation, and performance to guide engineers on practical application of bias mitigation.",
  "total_nodes": 29,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Practitioner's Guide to Mitigating Incorrect Inductive Biases in Deep Learning",
      "description": "This root frames the report as a step-by-step workflow for engineers to identify, implement, and verify strategies against inductive biases that cause poor generalization, drawing on academic_search and dataset_search for real-world experiments.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Deciding When to Address Inductive Biases",
      "description": "Outlines decision gates for practitioners to choose bias mitigation over alternatives, using academic_search to compare techniques based on project constraints like dataset size and domain.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Key Decision Gates for Technique Selection",
      "description": "Covers criteria like generalization gaps in initial tests to decide when to apply bias fixes versus standard training, with dataset_search providing examples from vision tasks.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "When to Choose Bias Mitigation Over Alternatives",
      "description": "Explains scenarios where biases like background color shortcuts in image classification outweigh benefits of simpler models, using web_search for case studies on trade-offs.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n2",
      "level": 2,
      "title": "Top Use Cases in Different Domains",
      "description": "Details domain-specific triggers, such as language model shortcuts in text classification, with academic_search retrieving experiments to inform when to intervene.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n2",
      "level": 2,
      "title": "Why Addressing Biases Improves Outcomes",
      "description": "Links decisions to measurable outcomes like accuracy drops in new environments, using dataset_search for quick benchmarks to guide practitioner choices.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n1",
      "level": 1,
      "title": "Implementing Mitigation Techniques",
      "description": "Provides step-by-step implementation for addressing incorrect biases, including code snippets and tools, with code_search and academic_search for verified methods.",
      "section_type": "chapter"
    },
    {
      "node_id": "n8",
      "parent_id": "n7",
      "level": 2,
      "title": "Step-by-Step for Vision Domain Biases",
      "description": "Guides on implementing data augmentation to counter background biases, using dataset_search for experiment setups and code_search for library integrations.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n7",
      "level": 2,
      "title": "Step-by-Step for Language Domain Biases",
      "description": "Outlines techniques like adversarial training for shortcut learning, with academic_search providing literature on decision points for parameter tuning.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n7",
      "level": 2,
      "title": "Handling Decision Points in Workflow",
      "description": "Covers branching choices, such as when to add regularization, using dataset_search for A/B test evidence to validate implementation paths.",
      "section_type": "section"
    },
    {
      "node_id": "n12",
      "parent_id": "n7",
      "level": 2,
      "title": "Integrating with Existing Pipelines",
      "description": "Explains how to insert bias checks into ML pipelines, with web_search for real-world examples of seamless integration decisions.",
      "section_type": "section"
    },
    {
      "node_id": "n13",
      "parent_id": "n1",
      "level": 1,
      "title": "Handling Edge Cases and Failure Modes",
      "description": "Identifies top failure modes of bias mitigation and recovery strategies, using dataset_search for detection experiments in various domains.",
      "section_type": "chapter"
    },
    {
      "node_id": "n14",
      "parent_id": "n13",
      "level": 2,
      "title": "Top-Three Failure Modes in Practice",
      "description": "Details modes like overfitting to spurious correlations, with academic_search providing experiments to help practitioners detect them early.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n13",
      "level": 2,
      "title": "Detecting Failure Modes in Vision Tasks",
      "description": "Outlines diagnostic tests for biases, such as cross-domain validation, using dataset_search for edge case datasets.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n13",
      "level": 2,
      "title": "Detecting Failure Modes in Language Tasks",
      "description": "Covers tools for spotting biases in text data, with forum_search for practitioner-reported issues and recovery tactics.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n13",
      "level": 2,
      "title": "Recovery Strategies for Each Mode",
      "description": "Provides actionable steps to fix detected failures, like retraining with balanced data, using academic_search for evidence-based methods.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n13",
      "level": 2,
      "title": "Edge Cases in Multi-Domain Applications",
      "description": "Addresses combined domain failures, with dataset_search for experiments illustrating decision points for escalation.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n1",
      "level": 1,
      "title": "Validating Bias Mitigation",
      "description": "Focuses on strategies to measure and audit successful bias handling, using academic_search and dataset_search for validation benchmarks.",
      "section_type": "chapter"
    },
    {
      "node_id": "n20",
      "parent_id": "n19",
      "level": 2,
      "title": "Measurement Techniques for Effectiveness",
      "description": "Explains metrics like out-of-distribution accuracy to verify mitigation, with dataset_search providing test sets for practical auditing.",
      "section_type": "section"
    },
    {
      "node_id": "n21",
      "parent_id": "n19",
      "level": 2,
      "title": "Auditing Protocols for Biases",
      "description": "Guides on systematic reviews of model decisions, using web_search for tools that flag potential issues in real-time.",
      "section_type": "section"
    },
    {
      "node_id": "n22",
      "parent_id": "n19",
      "level": 2,
      "title": "Testing Against Known Biases",
      "description": "Outlines experiments to simulate biases and confirm fixes, with academic_search for literature on validation setups.",
      "section_type": "section"
    },
    {
      "node_id": "n23",
      "parent_id": "n19",
      "level": 2,
      "title": "What 'Done Correctly' Looks Like",
      "description": "Defines success through testable outcomes, like consistent performance across environments, using dataset_search for benchmarks.",
      "section_type": "section"
    },
    {
      "node_id": "n24",
      "parent_id": "n19",
      "level": 2,
      "title": "Iterative Validation Workflows",
      "description": "Describes loops for ongoing checks, with forum_search for practitioner tips on integrating validation decisions.",
      "section_type": "section"
    },
    {
      "node_id": "n25",
      "parent_id": "n1",
      "level": 1,
      "title": "Performance Considerations and Advanced Topics",
      "description": "Evaluates trade-offs in mitigation techniques, using academic_search for complexity analysis to inform scaling decisions.",
      "section_type": "chapter"
    },
    {
      "node_id": "n26",
      "parent_id": "n25",
      "level": 2,
      "title": "Complexity and Resource Trade-Offs",
      "description": "Analyzes computational costs of bias fixes, with code_search for optimized implementations to guide practitioner choices.",
      "section_type": "section"
    },
    {
      "node_id": "n27",
      "parent_id": "n25",
      "level": 2,
      "title": "Scalability in Production Environments",
      "description": "Discusses adapting techniques for large-scale use, using dataset_search for evidence on performance under constraints.",
      "section_type": "section"
    },
    {
      "node_id": "n28",
      "parent_id": "n25",
      "level": 2,
      "title": "Suggested Solutions from Literature",
      "description": "Reviews methods like debiasing algorithms, with academic_search for experiments and decision points for adoption.",
      "section_type": "section"
    },
    {
      "node_id": "n29",
      "parent_id": "n25",
      "level": 2,
      "title": "Custom Practitioner Methods for Bias Addressing",
      "description": "Proposes novel approaches, such as hybrid data sampling, with web_search for validation ideas tailored to real-world workflows.",
      "section_type": "section"
    },
    {
      "node_id": "n30",
      "parent_id": "n25",
      "level": 2,
      "title": "Integration with Overall ML Strategy",
      "description": "Explains how to weave bias mitigation into broader strategies, using forum_search for practical performance insights.",
      "section_type": "section"
    }
  ]
}
```

