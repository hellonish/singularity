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
strength_context: target_section_count=19
available_retrieval_skills: dataset_search, patent_search, gov_search, social_search, book_search, data_extraction, standards_search, financial_search, web_search, pdf_deep_extract, video_search, forum_search, code_search, news_archive, clinical_search, legal_search, multimedia_search, academic_search
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

Produce exactly 19 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_1",
  "total_nodes": 19,
  "rationale": "This structure builds from foundational concepts and axioms to mathematical formalism, properties, and applications, ensuring practitioners understand the underlying reasons for inductive biases before exploring practical implementations.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Foundations of Inductive Biases in Deep Learning",
      "description": "This root frames the report by establishing a progression from core definitions and axioms to applications, using academic_search and book_search to ground the theoretical basis for why inductive biases lead to incorrect generalizations in deep learning models.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Definitions and Axioms",
      "description": "Introduces the minimal set of definitions needed for inductive biases, drawing on academic_search for foundational texts to explain why these axioms make certain generalizations inevitable in learning systems.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Minimal Definitions for Inductive Bias",
      "description": "Outlines key terms like inductive bias and generalization, using book_search to provide evidence from theoretical sources, focusing on first-principles that underpin why models prefer specific patterns.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Axioms in Machine Learning",
      "description": "Explores the axioms that make inductive biases non-arbitrary, leveraging academic_search for historical proofs and data_extraction to illustrate how these axioms constrain model behavior in deep learning.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Mathematical Formalism",
      "description": "Develops the mathematical structures underlying inductive biases, using academic_search for formal models to build from axioms to equations, highlighting where formalism diverges from intuition and why this matters for model reliability.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n5",
      "level": 2,
      "title": "Formal Models of Inductive Bias",
      "description": "Presents mathematical representations of biases, employing dataset_search and academic_search to derive equations from first-principles, focusing on why these models predict incorrect learning in deep networks.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n6",
      "level": 3,
      "title": "Equations and Derivations",
      "description": "Details specific derivations for bias equations, using pdf_deep_extract on academic papers to provide step-level formalism, addressing why divergences from intuition lead to flawed generalizations in practitioners' implementations.",
      "section_type": "subsection"
    },
    {
      "node_id": "n8",
      "parent_id": "n5",
      "level": 2,
      "title": "Intuition vs. Formalism in Biases",
      "description": "Examines where mathematical intuition diverges from formal proofs, utilizing book_search for comparative analyses, and explaining why this matters for avoiding incorrect biases in deep learning edge cases.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n1",
      "level": 1,
      "title": "Properties and Proofs",
      "description": "Analyzes the properties of inductive biases and their proofs, drawing on academic_search for theorems to demonstrate why certain biases are inevitable and lead to errors, preparing for validation in applications.",
      "section_type": "chapter"
    },
    {
      "node_id": "n10",
      "parent_id": "n9",
      "level": 2,
      "title": "Properties of Incorrect Inductive Biases",
      "description": "Outlines key properties like overfitting tendencies, using dataset_search for empirical evidence to show why these properties stem from foundational axioms in deep learning models.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n9",
      "level": 2,
      "title": "Proofs of Bias Failures",
      "description": "Provides rigorous proofs of why biases fail in generalization, leveraging academic_search for theorem-based evidence across domains like vision and language, focusing on the 'why' behind model errors.",
      "section_type": "section"
    },
    {
      "node_id": "n12",
      "parent_id": "n11",
      "level": 3,
      "title": "Specific Theorems and Counterexamples",
      "description": "Details theorems such as those related to PAC learning, using pdf_deep_extract for counterexamples in experiments, to illustrate why formalism reveals hidden failures in practitioner-level model training.",
      "section_type": "subsection"
    },
    {
      "node_id": "n13",
      "parent_id": "n1",
      "level": 1,
      "title": "Divergences and Implications",
      "description": "Investigates where mathematical and intuitive understandings diverge, using book_search for analyses to explain why this matters for deep learning reliability, bridging to practical implications.",
      "section_type": "chapter"
    },
    {
      "node_id": "n14",
      "parent_id": "n13",
      "level": 2,
      "title": "Where Intuition Diverges from Formalism",
      "description": "Explores specific divergences in bias interpretation, employing academic_search for case studies to demonstrate why these gaps cause incorrect learning in real-world scenarios.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n13",
      "level": 2,
      "title": "Implications for Deep Learning Models",
      "description": "Discusses the broader implications of these divergences, using dataset_search for validation data to show why addressing them is crucial for practitioner implementations.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n1",
      "level": 1,
      "title": "Real-World Applications",
      "description": "Applies the foundational understanding to practical scenarios, using dataset_search and video_search for experiments illustrating incorrect biases, now that the 'why' is established.",
      "section_type": "chapter"
    },
    {
      "node_id": "n17",
      "parent_id": "n16",
      "level": 2,
      "title": "Illustrating Incorrect Biases with Experiments",
      "description": "Presents experiments in domains like vision and language, leveraging dataset_search for real datasets to demonstrate bias failures and their edge cases in deep learning.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n16",
      "level": 2,
      "title": "Solutions from Literature and Innovations",
      "description": "Reviews literature-based solutions and suggests a new method, using academic_search and patent_search for evidence on addressing biases through regularization techniques.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n18",
      "level": 3,
      "title": "Proposed Method for Bias Mitigation",
      "description": "Outlines a novel practitioner-oriented method, drawing on code_search for implementation examples to validate how it counters divergences identified earlier.",
      "section_type": "subsection"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_1",
  "rationale": "This structure builds from foundational concepts and axioms to mathematical formalism, properties, and applications, ensuring practitioners understand the underlying reasons for inductive biases before exploring practical implementations.",
  "total_nodes": 19,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Foundations of Inductive Biases in Deep Learning",
      "description": "This root frames the report by establishing a progression from core definitions and axioms to applications, using academic_search and book_search to ground the theoretical basis for why inductive biases lead to incorrect generalizations in deep learning models.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Definitions and Axioms",
      "description": "Introduces the minimal set of definitions needed for inductive biases, drawing on academic_search for foundational texts to explain why these axioms make certain generalizations inevitable in learning systems.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Minimal Definitions for Inductive Bias",
      "description": "Outlines key terms like inductive bias and generalization, using book_search to provide evidence from theoretical sources, focusing on first-principles that underpin why models prefer specific patterns.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Axioms in Machine Learning",
      "description": "Explores the axioms that make inductive biases non-arbitrary, leveraging academic_search for historical proofs and data_extraction to illustrate how these axioms constrain model behavior in deep learning.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Mathematical Formalism",
      "description": "Develops the mathematical structures underlying inductive biases, using academic_search for formal models to build from axioms to equations, highlighting where formalism diverges from intuition and why this matters for model reliability.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n5",
      "level": 2,
      "title": "Formal Models of Inductive Bias",
      "description": "Presents mathematical representations of biases, employing dataset_search and academic_search to derive equations from first-principles, focusing on why these models predict incorrect learning in deep networks.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n6",
      "level": 3,
      "title": "Equations and Derivations",
      "description": "Details specific derivations for bias equations, using pdf_deep_extract on academic papers to provide step-level formalism, addressing why divergences from intuition lead to flawed generalizations in practitioners' implementations.",
      "section_type": "subsection"
    },
    {
      "node_id": "n8",
      "parent_id": "n5",
      "level": 2,
      "title": "Intuition vs. Formalism in Biases",
      "description": "Examines where mathematical intuition diverges from formal proofs, utilizing book_search for comparative analyses, and explaining why this matters for avoiding incorrect biases in deep learning edge cases.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n1",
      "level": 1,
      "title": "Properties and Proofs",
      "description": "Analyzes the properties of inductive biases and their proofs, drawing on academic_search for theorems to demonstrate why certain biases are inevitable and lead to errors, preparing for validation in applications.",
      "section_type": "chapter"
    },
    {
      "node_id": "n10",
      "parent_id": "n9",
      "level": 2,
      "title": "Properties of Incorrect Inductive Biases",
      "description": "Outlines key properties like overfitting tendencies, using dataset_search for empirical evidence to show why these properties stem from foundational axioms in deep learning models.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n9",
      "level": 2,
      "title": "Proofs of Bias Failures",
      "description": "Provides rigorous proofs of why biases fail in generalization, leveraging academic_search for theorem-based evidence across domains like vision and language, focusing on the 'why' behind model errors.",
      "section_type": "section"
    },
    {
      "node_id": "n12",
      "parent_id": "n11",
      "level": 3,
      "title": "Specific Theorems and Counterexamples",
      "description": "Details theorems such as those related to PAC learning, using pdf_deep_extract for counterexamples in experiments, to illustrate why formalism reveals hidden failures in practitioner-level model training.",
      "section_type": "subsection"
    },
    {
      "node_id": "n13",
      "parent_id": "n1",
      "level": 1,
      "title": "Divergences and Implications",
      "description": "Investigates where mathematical and intuitive understandings diverge, using book_search for analyses to explain why this matters for deep learning reliability, bridging to practical implications.",
      "section_type": "chapter"
    },
    {
      "node_id": "n14",
      "parent_id": "n13",
      "level": 2,
      "title": "Where Intuition Diverges from Formalism",
      "description": "Explores specific divergences in bias interpretation, employing academic_search for case studies to demonstrate why these gaps cause incorrect learning in real-world scenarios.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n13",
      "level": 2,
      "title": "Implications for Deep Learning Models",
      "description": "Discusses the broader implications of these divergences, using dataset_search for validation data to show why addressing them is crucial for practitioner implementations.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n1",
      "level": 1,
      "title": "Real-World Applications",
      "description": "Applies the foundational understanding to practical scenarios, using dataset_search and video_search for experiments illustrating incorrect biases, now that the 'why' is established.",
      "section_type": "chapter"
    },
    {
      "node_id": "n17",
      "parent_id": "n16",
      "level": 2,
      "title": "Illustrating Incorrect Biases with Experiments",
      "description": "Presents experiments in domains like vision and language, leveraging dataset_search for real datasets to demonstrate bias failures and their edge cases in deep learning.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n16",
      "level": 2,
      "title": "Solutions from Literature and Innovations",
      "description": "Reviews literature-based solutions and suggests a new method, using academic_search and patent_search for evidence on addressing biases through regularization techniques.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n18",
      "level": 3,
      "title": "Proposed Method for Bias Mitigation",
      "description": "Outlines a novel practitioner-oriented method, drawing on code_search for implementation examples to validate how it counters divergences identified earlier.",
      "section_type": "subsection"
    }
  ]
}
```

