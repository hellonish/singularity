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
strength_context: target_section_count=19
available_retrieval_skills: dataset_search, patent_search, gov_search, social_search, book_search, data_extraction, standards_search, financial_search, web_search, pdf_deep_extract, video_search, forum_search, code_search, news_archive, clinical_search, legal_search, multimedia_search, academic_search
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

Produce exactly 19 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_3",
  "total_nodes": 19,
  "rationale": "This structure follows a practitioner's workflow by sequencing decisions on usage, implementation steps, failure handling, validation, and performance to guide engineers through real-world application.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Practitioner's Guide to Handling Incorrect Inductive Biases in Deep Learning",
      "description": "This report outlines a workflow for engineers to identify, mitigate, and validate incorrect inductive biases in deep learning models across domains like vision and language, using practical steps and evidence from academic and experimental sources.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "When and Why to Address Incorrect Inductive Biases",
      "description": "Explains decision gates for choosing techniques to handle inductive biases, including comparisons to alternatives like regularization methods, drawing on academic_search for literature on when biases lead to poor generalization in real deployments.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Decision Gates for Technique Selection",
      "description": "Covers criteria for selecting bias mitigation over other methods, such as when data patterns mislead models, using dataset_search to pull examples from vision datasets like ImageNet for quick comparisons.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Alternatives and Trade-offs",
      "description": "Outlines when to use alternatives like ensemble methods, with evidence from academic_search on their effectiveness versus bias-specific techniques in language models.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n2",
      "level": 2,
      "title": "Why Prioritize in High-Stakes Domains",
      "description": "Discusses scenarios in vision or language where biases cause failures, using web_search for case studies on real-world errors in autonomous systems.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "Step-by-Step Implementation of Bias Mitigation",
      "description": "Provides a sequence of actionable steps for implementing experiments to illustrate and address incorrect inductive biases, incorporating theory only where it informs decisions like model selection.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n6",
      "level": 2,
      "title": "Initial Experiment Setup",
      "description": "Details steps to set up datasets for testing biases, such as creating synthetic vision data with biased backgrounds, using dataset_search and code_search for scripts.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n6",
      "level": 2,
      "title": "Model Training with Decision Points",
      "description": "Guides on training decisions, like adjusting hyperparameters to counter biases, with code_search for implementation examples in PyTorch.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n6",
      "level": 2,
      "title": "Iterative Testing and Adjustment",
      "description": "Outlines loops for testing model outputs, using data_extraction to analyze results from experiments across domains.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n6",
      "level": 2,
      "title": "Final Integration Checks",
      "description": "Covers verifying integration into workflows, with evidence from forum_search on common practitioner pitfalls.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n1",
      "level": 1,
      "title": "Common Edge Cases and Failure Modes",
      "description": "Identifies top-3 failure modes of inductive biases in deep learning and strategies for detection and recovery, focusing on practical scenarios in vision and language.",
      "section_type": "chapter"
    },
    {
      "node_id": "n12",
      "parent_id": "n11",
      "level": 2,
      "title": "Failure Mode 1: Background Dominance",
      "description": "Explains detection of biases like color-based fruit classification and recovery steps, using video_search for experimental illustrations.",
      "section_type": "section"
    },
    {
      "node_id": "n13",
      "parent_id": "n11",
      "level": 2,
      "title": "Failure Mode 2: Domain Shifts",
      "description": "Details how to identify shifts in language data and recover via retraining, with academic_search for evidence from NLP benchmarks.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n11",
      "level": 2,
      "title": "Failure Mode 3: Overfitting to Noise",
      "description": "Covers detection in vision models and recovery techniques, using dataset_search for noisy data examples.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n1",
      "level": 1,
      "title": "Validation Strategies for Bias Mitigation",
      "description": "Outlines methods to measure and audit successful bias handling, ensuring 'done correctly' through testing and metrics.",
      "section_type": "chapter"
    },
    {
      "node_id": "n16",
      "parent_id": "n15",
      "level": 2,
      "title": "Metric Selection and Testing",
      "description": "Guides on choosing validation metrics like accuracy drops, with data_extraction from experiments to verify outcomes.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n15",
      "level": 2,
      "title": "Cross-Domain Validation",
      "description": "Steps for validating across domains, using multimedia_search for diverse test sets.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n15",
      "level": 2,
      "title": "Auditing for Completeness",
      "description": "Explains how to audit implementations for full bias coverage, including a subsection on automated tools.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n18",
      "level": 3,
      "title": "Automated Tool Integration",
      "description": "Focuses on using code_search for tools that automate bias checks, providing step-level guidance on integration and evidence from open-source repositories.",
      "section_type": "subsection"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_3",
  "rationale": "This structure follows a practitioner's workflow by sequencing decisions on usage, implementation steps, failure handling, validation, and performance to guide engineers through real-world application.",
  "total_nodes": 19,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Practitioner's Guide to Handling Incorrect Inductive Biases in Deep Learning",
      "description": "This report outlines a workflow for engineers to identify, mitigate, and validate incorrect inductive biases in deep learning models across domains like vision and language, using practical steps and evidence from academic and experimental sources.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "When and Why to Address Incorrect Inductive Biases",
      "description": "Explains decision gates for choosing techniques to handle inductive biases, including comparisons to alternatives like regularization methods, drawing on academic_search for literature on when biases lead to poor generalization in real deployments.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Decision Gates for Technique Selection",
      "description": "Covers criteria for selecting bias mitigation over other methods, such as when data patterns mislead models, using dataset_search to pull examples from vision datasets like ImageNet for quick comparisons.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Alternatives and Trade-offs",
      "description": "Outlines when to use alternatives like ensemble methods, with evidence from academic_search on their effectiveness versus bias-specific techniques in language models.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n2",
      "level": 2,
      "title": "Why Prioritize in High-Stakes Domains",
      "description": "Discusses scenarios in vision or language where biases cause failures, using web_search for case studies on real-world errors in autonomous systems.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "Step-by-Step Implementation of Bias Mitigation",
      "description": "Provides a sequence of actionable steps for implementing experiments to illustrate and address incorrect inductive biases, incorporating theory only where it informs decisions like model selection.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n6",
      "level": 2,
      "title": "Initial Experiment Setup",
      "description": "Details steps to set up datasets for testing biases, such as creating synthetic vision data with biased backgrounds, using dataset_search and code_search for scripts.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n6",
      "level": 2,
      "title": "Model Training with Decision Points",
      "description": "Guides on training decisions, like adjusting hyperparameters to counter biases, with code_search for implementation examples in PyTorch.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n6",
      "level": 2,
      "title": "Iterative Testing and Adjustment",
      "description": "Outlines loops for testing model outputs, using data_extraction to analyze results from experiments across domains.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n6",
      "level": 2,
      "title": "Final Integration Checks",
      "description": "Covers verifying integration into workflows, with evidence from forum_search on common practitioner pitfalls.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n1",
      "level": 1,
      "title": "Common Edge Cases and Failure Modes",
      "description": "Identifies top-3 failure modes of inductive biases in deep learning and strategies for detection and recovery, focusing on practical scenarios in vision and language.",
      "section_type": "chapter"
    },
    {
      "node_id": "n12",
      "parent_id": "n11",
      "level": 2,
      "title": "Failure Mode 1: Background Dominance",
      "description": "Explains detection of biases like color-based fruit classification and recovery steps, using video_search for experimental illustrations.",
      "section_type": "section"
    },
    {
      "node_id": "n13",
      "parent_id": "n11",
      "level": 2,
      "title": "Failure Mode 2: Domain Shifts",
      "description": "Details how to identify shifts in language data and recover via retraining, with academic_search for evidence from NLP benchmarks.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n11",
      "level": 2,
      "title": "Failure Mode 3: Overfitting to Noise",
      "description": "Covers detection in vision models and recovery techniques, using dataset_search for noisy data examples.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n1",
      "level": 1,
      "title": "Validation Strategies for Bias Mitigation",
      "description": "Outlines methods to measure and audit successful bias handling, ensuring 'done correctly' through testing and metrics.",
      "section_type": "chapter"
    },
    {
      "node_id": "n16",
      "parent_id": "n15",
      "level": 2,
      "title": "Metric Selection and Testing",
      "description": "Guides on choosing validation metrics like accuracy drops, with data_extraction from experiments to verify outcomes.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n15",
      "level": 2,
      "title": "Cross-Domain Validation",
      "description": "Steps for validating across domains, using multimedia_search for diverse test sets.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n15",
      "level": 2,
      "title": "Auditing for Completeness",
      "description": "Explains how to audit implementations for full bias coverage, including a subsection on automated tools.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n18",
      "level": 3,
      "title": "Automated Tool Integration",
      "description": "Focuses on using code_search for tools that automate bias checks, providing step-level guidance on integration and evidence from open-source repositories.",
      "section_type": "subsection"
    }
  ]
}
```

