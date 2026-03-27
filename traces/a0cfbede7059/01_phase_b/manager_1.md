# Manager 1 — Report Structure Proposal

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
proposal_id: manager_1
structural_perspective: concept-first
perspective_instruction:
ROLE: You are a foundational-theory architect. Your structure reveals WHY something works, not just what it does. You begin at axioms and build outward so a reader achieves deep conceptual understanding before encountering any applied examples.

STRUCTURE PRINCIPLE: Organise from foundational theory outward: start with definitions and axioms, build through mathematical formalism, then move to properties, proofs, and finally real-world applications. A reader should understand the 'why' deeply before encountering any worked examples.

KEY QUESTIONS — your tree must answer these:
  - What is the minimal set of definitions needed to ground everything else?
  - What first-principles make this technique inevitable rather than arbitrary?
  - Where do the mathematical formalism and the intuition diverge — and why does that matter?

ANTI-PATTERNS — explicitly avoid:
  ✗ Do NOT open with a use case before establishing the conceptual foundation.
  ✗ Do NOT bury the formal definition inside an application section.
  ✗ Do NOT write a chapter titled 'Introduction' that is just background — make it a conceptual claim.

Produce exactly 28 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_1",
  "total_nodes": 28,
  "rationale": "This structure organizes the report from foundational definitions and axioms to mathematical formalism, properties, proofs, and finally applications, ensuring readers grasp the underlying 'why' of inductive biases before addressing real-world implications.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Building Deep Conceptual Foundations for Inductive Biases in Deep Learning",
      "description": "This root frames the report by starting with the essential axioms of inductive biases to explain why deep learning models prefer certain generalizations, using academic_search for theoretical grounding before progressing to applications.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Definitions and Axioms of Inductive Bias",
      "description": "Establishes the minimal set of definitions and first-principles that make inductive biases inevitable in learning systems, drawing from academic_search to define key concepts like generalization preferences without yet touching applications.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n1",
      "level": 1,
      "title": "Mathematical Formalism of Inductive Bias",
      "description": "Develops the formal mathematical structures underlying inductive biases, including where intuition diverges from formalism, using academic_search for theorems and equations to build a rigorous foundation before any empirical examples.",
      "section_type": "chapter"
    },
    {
      "node_id": "n4",
      "parent_id": "n1",
      "level": 1,
      "title": "Properties and Proofs of Inductive Biases",
      "description": "Explores the inherent properties and proofs that reveal why certain inductive biases lead to incorrect generalizations, leveraging academic_search for formal derivations to highlight divergences between theory and practice.",
      "section_type": "chapter"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Real-World Applications and Experiments of Incorrect Inductive Biases",
      "description": "Applies the established foundations to illustrate why incorrect biases occur in deep learning, using dataset_search and video_search for experimental setups across domains like vision and language.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "Addressing Incorrect Inductive Biases: Solutions and Methods",
      "description": "Extends from prior proofs to propose solutions for mitigating biases, drawing on academic_search and patent_search for literature-based methods and original ideas, ensuring conceptual understanding informs practical fixes.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n2",
      "level": 2,
      "title": "Defining Inductive Bias in Learning Systems",
      "description": "Outlines the basic axioms of inductive bias as a preference mechanism, using academic_search to ground definitions in first-principles like Occam's razor, explaining why these are necessary for any learning framework.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n2",
      "level": 2,
      "title": "Axioms of Generalization Preferences",
      "description": "Identifies the core axioms that dictate why systems favor certain hypotheses, employing book_search for historical contexts to show these principles are not arbitrary but stem from information theory.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n2",
      "level": 2,
      "title": "Minimal Set of Definitions for Deep Learning Biases",
      "description": "Defines the precise terms needed to understand bias in neural networks, using academic_search to clarify why these definitions must precede any discussion of incorrect biases.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n3",
      "level": 2,
      "title": "Formal Equations for Inductive Bias",
      "description": "Presents the mathematical formalism for how biases are encoded in loss functions, using academic_search to derive equations that show why certain preferences emerge from optimization.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n3",
      "level": 2,
      "title": "Divergence Between Formalism and Intuition",
      "description": "Analyzes where mathematical models of bias diverge from intuitive understandings, employing academic_search to explain the implications for deep learning theory.",
      "section_type": "section"
    },
    {
      "node_id": "n12",
      "parent_id": "n3",
      "level": 2,
      "title": "First-Principles Derivations in Neural Architectures",
      "description": "Derives the formalism for biases in architectures like CNNs, using academic_search to illustrate why these structures are inevitable based on data representation principles.",
      "section_type": "section"
    },
    {
      "node_id": "n13",
      "parent_id": "n3",
      "level": 2,
      "title": "Mathematical Intuition for Bias Propagation",
      "description": "Explores how biases propagate through layers via matrix operations, drawing from academic_search to highlight why this matters for conceptual understanding.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n4",
      "level": 2,
      "title": "Properties of Incorrect Inductive Biases",
      "description": "Examines key properties that make biases incorrect, such as overfitting tendencies, using academic_search for proofs that demonstrate why these properties arise from foundational axioms.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n4",
      "level": 2,
      "title": "Proofs of Bias in Vision Domains",
      "description": "Provides formal proofs for why biases lead to failures in vision tasks, leveraging dataset_search to support theoretical arguments with empirical validation.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n4",
      "level": 2,
      "title": "Proofs of Bias in Language Domains",
      "description": "Delivers proofs showing why language models exhibit incorrect biases, using academic_search for derivations and including subsections for specific cases.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n4",
      "level": 2,
      "title": "Divergence in Proofs Across Domains",
      "description": "Compares proofs across domains to explain why formalism diverges from intuition, employing academic_search to underscore the theoretical implications.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n4",
      "level": 2,
      "title": "Edge Cases in Bias Properties",
      "description": "Analyzes edge cases where proofs reveal unexpected bias behaviors, using dataset_search for validation to prepare for applications.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n5",
      "level": 2,
      "title": "Experimental Illustrations in Vision",
      "description": "Applies foundations to vision experiments showing incorrect biases, like background color preferences, using dataset_search for real datasets and video_search for demonstrations.",
      "section_type": "section"
    },
    {
      "node_id": "n20",
      "parent_id": "n5",
      "level": 2,
      "title": "Experimental Illustrations in Language",
      "description": "Illustrates language biases through experiments, such as shortcut learning, employing dataset_search to provide empirical evidence based on prior proofs.",
      "section_type": "section"
    },
    {
      "node_id": "n21",
      "parent_id": "n5",
      "level": 2,
      "title": "Validation of Incorrect Biases Across Domains",
      "description": "Validates why biases fail to generalize using controlled experiments, drawing from dataset_search and academic_search for comparative analysis.",
      "section_type": "section"
    },
    {
      "node_id": "n22",
      "parent_id": "n5",
      "level": 2,
      "title": "Implementation Considerations for Experiments",
      "description": "Discusses practical implementation of bias experiments, using code_search for code examples to ensure alignment with theoretical properties.",
      "section_type": "section"
    },
    {
      "node_id": "n23",
      "parent_id": "n6",
      "level": 2,
      "title": "Literature-Based Solutions for Biases",
      "description": "Reviews solutions from the literature, such as regularization techniques, using academic_search to explain why they address biases based on prior proofs.",
      "section_type": "section"
    },
    {
      "node_id": "n24",
      "parent_id": "n6",
      "level": 2,
      "title": "Proposed Methods to Mitigate Biases",
      "description": "Suggests original methods for bias correction, drawing from patent_search to integrate innovative approaches with conceptual foundations.",
      "section_type": "section"
    },
    {
      "node_id": "n25",
      "parent_id": "n6",
      "level": 2,
      "title": "Validation of Bias Solutions",
      "description": "Evaluates the effectiveness of solutions through theoretical and empirical validation, using dataset_search for experiments tied to earlier proofs.",
      "section_type": "section"
    },
    {
      "node_id": "n26",
      "parent_id": "n16",
      "level": 3,
      "title": "Proof Subcase: Syntactic Biases in Language",
      "description": "Focuses on a subcase of proofs for language biases, like positional encodings, using academic_search for detailed derivations to show why these differ from vision cases.",
      "section_type": "subsection"
    },
    {
      "node_id": "n27",
      "parent_id": "n16",
      "level": 3,
      "title": "Proof Subcase: Semantic Biases in Language",
      "description": "Examines another subcase of proofs for semantic-related biases, employing academic_search to highlight divergences and their theoretical implications.",
      "section_type": "subsection"
    },
    {
      "node_id": "n28",
      "parent_id": "n16",
      "level": 3,
      "title": "Proof Subcase: Cross-Domain Comparisons",
      "description": "Compares subcases across domains in proofs, using academic_search to explain why intuition fails in these contexts, building on the chapter's core arguments.",
      "section_type": "subsection"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_1",
  "rationale": "This structure organizes the report from foundational definitions and axioms to mathematical formalism, properties, proofs, and finally applications, ensuring readers grasp the underlying 'why' of inductive biases before addressing real-world implications.",
  "total_nodes": 28,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Building Deep Conceptual Foundations for Inductive Biases in Deep Learning",
      "description": "This root frames the report by starting with the essential axioms of inductive biases to explain why deep learning models prefer certain generalizations, using academic_search for theoretical grounding before progressing to applications.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Definitions and Axioms of Inductive Bias",
      "description": "Establishes the minimal set of definitions and first-principles that make inductive biases inevitable in learning systems, drawing from academic_search to define key concepts like generalization preferences without yet touching applications.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n1",
      "level": 1,
      "title": "Mathematical Formalism of Inductive Bias",
      "description": "Develops the formal mathematical structures underlying inductive biases, including where intuition diverges from formalism, using academic_search for theorems and equations to build a rigorous foundation before any empirical examples.",
      "section_type": "chapter"
    },
    {
      "node_id": "n4",
      "parent_id": "n1",
      "level": 1,
      "title": "Properties and Proofs of Inductive Biases",
      "description": "Explores the inherent properties and proofs that reveal why certain inductive biases lead to incorrect generalizations, leveraging academic_search for formal derivations to highlight divergences between theory and practice.",
      "section_type": "chapter"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Real-World Applications and Experiments of Incorrect Inductive Biases",
      "description": "Applies the established foundations to illustrate why incorrect biases occur in deep learning, using dataset_search and video_search for experimental setups across domains like vision and language.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "Addressing Incorrect Inductive Biases: Solutions and Methods",
      "description": "Extends from prior proofs to propose solutions for mitigating biases, drawing on academic_search and patent_search for literature-based methods and original ideas, ensuring conceptual understanding informs practical fixes.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n2",
      "level": 2,
      "title": "Defining Inductive Bias in Learning Systems",
      "description": "Outlines the basic axioms of inductive bias as a preference mechanism, using academic_search to ground definitions in first-principles like Occam's razor, explaining why these are necessary for any learning framework.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n2",
      "level": 2,
      "title": "Axioms of Generalization Preferences",
      "description": "Identifies the core axioms that dictate why systems favor certain hypotheses, employing book_search for historical contexts to show these principles are not arbitrary but stem from information theory.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n2",
      "level": 2,
      "title": "Minimal Set of Definitions for Deep Learning Biases",
      "description": "Defines the precise terms needed to understand bias in neural networks, using academic_search to clarify why these definitions must precede any discussion of incorrect biases.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n3",
      "level": 2,
      "title": "Formal Equations for Inductive Bias",
      "description": "Presents the mathematical formalism for how biases are encoded in loss functions, using academic_search to derive equations that show why certain preferences emerge from optimization.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n3",
      "level": 2,
      "title": "Divergence Between Formalism and Intuition",
      "description": "Analyzes where mathematical models of bias diverge from intuitive understandings, employing academic_search to explain the implications for deep learning theory.",
      "section_type": "section"
    },
    {
      "node_id": "n12",
      "parent_id": "n3",
      "level": 2,
      "title": "First-Principles Derivations in Neural Architectures",
      "description": "Derives the formalism for biases in architectures like CNNs, using academic_search to illustrate why these structures are inevitable based on data representation principles.",
      "section_type": "section"
    },
    {
      "node_id": "n13",
      "parent_id": "n3",
      "level": 2,
      "title": "Mathematical Intuition for Bias Propagation",
      "description": "Explores how biases propagate through layers via matrix operations, drawing from academic_search to highlight why this matters for conceptual understanding.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n4",
      "level": 2,
      "title": "Properties of Incorrect Inductive Biases",
      "description": "Examines key properties that make biases incorrect, such as overfitting tendencies, using academic_search for proofs that demonstrate why these properties arise from foundational axioms.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n4",
      "level": 2,
      "title": "Proofs of Bias in Vision Domains",
      "description": "Provides formal proofs for why biases lead to failures in vision tasks, leveraging dataset_search to support theoretical arguments with empirical validation.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n4",
      "level": 2,
      "title": "Proofs of Bias in Language Domains",
      "description": "Delivers proofs showing why language models exhibit incorrect biases, using academic_search for derivations and including subsections for specific cases.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n4",
      "level": 2,
      "title": "Divergence in Proofs Across Domains",
      "description": "Compares proofs across domains to explain why formalism diverges from intuition, employing academic_search to underscore the theoretical implications.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n4",
      "level": 2,
      "title": "Edge Cases in Bias Properties",
      "description": "Analyzes edge cases where proofs reveal unexpected bias behaviors, using dataset_search for validation to prepare for applications.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n5",
      "level": 2,
      "title": "Experimental Illustrations in Vision",
      "description": "Applies foundations to vision experiments showing incorrect biases, like background color preferences, using dataset_search for real datasets and video_search for demonstrations.",
      "section_type": "section"
    },
    {
      "node_id": "n20",
      "parent_id": "n5",
      "level": 2,
      "title": "Experimental Illustrations in Language",
      "description": "Illustrates language biases through experiments, such as shortcut learning, employing dataset_search to provide empirical evidence based on prior proofs.",
      "section_type": "section"
    },
    {
      "node_id": "n21",
      "parent_id": "n5",
      "level": 2,
      "title": "Validation of Incorrect Biases Across Domains",
      "description": "Validates why biases fail to generalize using controlled experiments, drawing from dataset_search and academic_search for comparative analysis.",
      "section_type": "section"
    },
    {
      "node_id": "n22",
      "parent_id": "n5",
      "level": 2,
      "title": "Implementation Considerations for Experiments",
      "description": "Discusses practical implementation of bias experiments, using code_search for code examples to ensure alignment with theoretical properties.",
      "section_type": "section"
    },
    {
      "node_id": "n23",
      "parent_id": "n6",
      "level": 2,
      "title": "Literature-Based Solutions for Biases",
      "description": "Reviews solutions from the literature, such as regularization techniques, using academic_search to explain why they address biases based on prior proofs.",
      "section_type": "section"
    },
    {
      "node_id": "n24",
      "parent_id": "n6",
      "level": 2,
      "title": "Proposed Methods to Mitigate Biases",
      "description": "Suggests original methods for bias correction, drawing from patent_search to integrate innovative approaches with conceptual foundations.",
      "section_type": "section"
    },
    {
      "node_id": "n25",
      "parent_id": "n6",
      "level": 2,
      "title": "Validation of Bias Solutions",
      "description": "Evaluates the effectiveness of solutions through theoretical and empirical validation, using dataset_search for experiments tied to earlier proofs.",
      "section_type": "section"
    },
    {
      "node_id": "n26",
      "parent_id": "n16",
      "level": 3,
      "title": "Proof Subcase: Syntactic Biases in Language",
      "description": "Focuses on a subcase of proofs for language biases, like positional encodings, using academic_search for detailed derivations to show why these differ from vision cases.",
      "section_type": "subsection"
    },
    {
      "node_id": "n27",
      "parent_id": "n16",
      "level": 3,
      "title": "Proof Subcase: Semantic Biases in Language",
      "description": "Examines another subcase of proofs for semantic-related biases, employing academic_search to highlight divergences and their theoretical implications.",
      "section_type": "subsection"
    },
    {
      "node_id": "n28",
      "parent_id": "n16",
      "level": 3,
      "title": "Proof Subcase: Cross-Domain Comparisons",
      "description": "Compares subcases across domains in proofs, using academic_search to explain why intuition fails in these contexts, building on the chapter's core arguments.",
      "section_type": "subsection"
    }
  ]
}
```

