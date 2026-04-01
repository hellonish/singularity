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

query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method.
strength_context: target_section_count=29
available_retrieval_skills: dataset_search, book_search, patent_search, data_extraction, pdf_deep_extract, clinical_search, standards_search, legal_search, news_archive, forum_search, code_search, financial_search, multimedia_search, gov_search, video_search, academic_search, web_search, social_search
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

Produce exactly 29 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_1",
  "total_nodes": 29,
  "rationale": "This structure organizes the report from foundational definitions and axioms of inductive biases in deep learning, through mathematical formalism and proofs, to practical applications, ensuring readers grasp the underlying 'why' before engaging with real-world examples.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Foundational Theory of Inductive Biases in Deep Learning",
      "description": "This root frames the report by establishing inductive biases as inherent preferences in learning systems, drawing from first-principles to build conceptual understanding, using academic_search and book_search for axiomatic definitions.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Definitions and Axioms",
      "description": "Introduces the minimal set of definitions for inductive biases, explaining why they arise from fundamental learning principles rather than arbitrary choices, using academic_search for theoretical texts.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Core Definitions of Inductive Biases",
      "description": "Defines key terms like generalization and bias in deep learning, exploring first-principles that make these inevitable, with evidence from book_search on foundational AI texts.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Axioms Underlying Learning Systems",
      "description": "Outlines axioms such as Occam's razor and data priors that ground inductive biases, using academic_search to retrieve formal statements and explain their inevitability.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n2",
      "level": 2,
      "title": "Distinction Between Correct and Incorrect Biases",
      "description": "Defines what constitutes an incorrect inductive bias and why it stems from flawed axioms, incorporating data_extraction from provided articles to highlight foundational divergences.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "Mathematical Formalism",
      "description": "Develops the mathematical structures of inductive biases, building on axioms to formalize how they influence learning, using pdf_deep_extract for equations from research papers.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n6",
      "level": 2,
      "title": "Formal Representation of Biases",
      "description": "Presents mathematical models like Bayesian priors for biases, explaining why formalism diverges from intuition in capturing generalization, with academic_search for relevant theorems.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n6",
      "level": 2,
      "title": "Equations for Bias in Neural Networks",
      "description": "Derives equations showing how biases affect weight updates, using code_search to pull pseudocode from implementations and highlight formal-intuition gaps.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n6",
      "level": 2,
      "title": "Impact on Optimization Landscapes",
      "description": "Formalizes how biases alter loss surfaces, with evidence from dataset_search on simulated experiments, emphasizing why this matters for learning dynamics.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n6",
      "level": 2,
      "title": "Divergence in Formal and Intuitive Models",
      "description": "Analyzes where mathematical formalism and intuitive understanding part ways, such as in non-convex optimization, using book_search for critiques from AI theory.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n6",
      "level": 2,
      "title": "Proofs of Bias Stability",
      "description": "Provides proofs for the stability of inductive biases under perturbations, drawing from academic_search to underscore first-principles necessity.",
      "section_type": "section"
    },
    {
      "node_id": "n12",
      "parent_id": "n1",
      "level": 1,
      "title": "Properties and Proofs",
      "description": "Explores properties of inductive biases through rigorous proofs, revealing why certain biases lead to incorrect generalizations, using patent_search for validated theoretical frameworks.",
      "section_type": "chapter"
    },
    {
      "node_id": "n13",
      "parent_id": "n12",
      "level": 2,
      "title": "Key Properties of Incorrect Biases",
      "description": "Details properties like brittleness and overfitting tendencies, with proofs from academic_search showing their derivation from core axioms.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n12",
      "level": 2,
      "title": "Proofs of Generalization Failure",
      "description": "Offers mathematical proofs demonstrating why incorrect biases fail to generalize, using video_search from the provided talk for illustrative derivations.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n12",
      "level": 2,
      "title": "Edge Cases in Bias Properties",
      "description": "Examines edge cases where biases amplify errors, with evidence from dataset_search on vision and language domains, including implementation considerations.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n12",
      "level": 2,
      "title": "Validation of Proofs Through Simulations",
      "description": "Validates theoretical proofs with simulated experiments, using code_search for scripts that test bias properties in controlled settings.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n12",
      "level": 2,
      "title": "Divergence in Proof Assumptions",
      "description": "Analyzes why proof assumptions sometimes diverge from real-world intuitions, drawing from forum_search discussions on AI limitations.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n1",
      "level": 1,
      "title": "Incorrect Inductive Biases in Domains",
      "description": "Applies foundational theory to identify and prove incorrect biases in specific domains, ensuring conceptual depth before examples.",
      "section_type": "chapter"
    },
    {
      "node_id": "n19",
      "parent_id": "n18",
      "level": 2,
      "title": "Vision Domain Biases",
      "description": "Identifies biases like background dependencies, with proofs of their incorrectness from academic_search, preparing for later experimental validation.",
      "section_type": "section"
    },
    {
      "node_id": "n20",
      "parent_id": "n18",
      "level": 2,
      "title": "Language Domain Biases",
      "description": "Explores biases in token embeddings, proving their failure in generalization using dataset_search for linguistic corpora.",
      "section_type": "section"
    },
    {
      "node_id": "n21",
      "parent_id": "n18",
      "level": 2,
      "title": "Cross-Domain Bias Interactions",
      "description": "Proves how biases transfer across domains, with evidence from web_search on multi-modal learning failures.",
      "section_type": "section"
    },
    {
      "node_id": "n22",
      "parent_id": "n18",
      "level": 2,
      "title": "Experimental Design for Bias Illustration",
      "description": "Outlines experiments to illustrate biases, using news_archive for real-world case studies, balanced with theoretical grounding.",
      "section_type": "section"
    },
    {
      "node_id": "n23",
      "parent_id": "n1",
      "level": 1,
      "title": "Addressing Inductive Biases",
      "description": "Transitions to solutions by proving methods to mitigate biases, drawing from established literature before suggesting innovations.",
      "section_type": "chapter"
    },
    {
      "node_id": "n24",
      "parent_id": "n23",
      "level": 2,
      "title": "Literature-Based Solutions",
      "description": "Reviews solutions like regularization techniques, with proofs of their effectiveness from academic_search, including implementation details.",
      "section_type": "section"
    },
    {
      "node_id": "n25",
      "parent_id": "n23",
      "level": 2,
      "title": "Validation of Mitigation Strategies",
      "description": "Provides edge-case validations for bias correction, using dataset_search for experimental data on various domains.",
      "section_type": "section"
    },
    {
      "node_id": "n26",
      "parent_id": "n23",
      "level": 2,
      "title": "Proposed New Method for Bias Reduction",
      "description": "Suggests a novel hybrid approach combining priors and adversarial training, with rationale from first-principles and code_search for prototypes.",
      "section_type": "section"
    },
    {
      "node_id": "n27",
      "parent_id": "n26",
      "level": 3,
      "title": "Step-by-Step Implementation",
      "description": "Details the implementation steps of the proposed method, including code snippets from code_search and validation tests for practitioners.",
      "section_type": "subsection"
    },
    {
      "node_id": "n28",
      "parent_id": "n23",
      "level": 2,
      "title": "Comparative Proofs of Solutions",
      "description": "Compares solution efficacy through proofs, using patent_search for patented techniques and highlighting divergence from intuitive fixes.",
      "section_type": "section"
    },
    {
      "node_id": "n29",
      "parent_id": "n28",
      "level": 3,
      "title": "Edge Case Analysis",
      "description": "Analyzes edge cases in solution proofs, with evidence from social_search on practitioner forums to ensure practical relevance.",
      "section_type": "subsection"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_1",
  "rationale": "This structure organizes the report from foundational definitions and axioms of inductive biases in deep learning, through mathematical formalism and proofs, to practical applications, ensuring readers grasp the underlying 'why' before engaging with real-world examples.",
  "total_nodes": 29,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Foundational Theory of Inductive Biases in Deep Learning",
      "description": "This root frames the report by establishing inductive biases as inherent preferences in learning systems, drawing from first-principles to build conceptual understanding, using academic_search and book_search for axiomatic definitions.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Definitions and Axioms",
      "description": "Introduces the minimal set of definitions for inductive biases, explaining why they arise from fundamental learning principles rather than arbitrary choices, using academic_search for theoretical texts.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Core Definitions of Inductive Biases",
      "description": "Defines key terms like generalization and bias in deep learning, exploring first-principles that make these inevitable, with evidence from book_search on foundational AI texts.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Axioms Underlying Learning Systems",
      "description": "Outlines axioms such as Occam's razor and data priors that ground inductive biases, using academic_search to retrieve formal statements and explain their inevitability.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n2",
      "level": 2,
      "title": "Distinction Between Correct and Incorrect Biases",
      "description": "Defines what constitutes an incorrect inductive bias and why it stems from flawed axioms, incorporating data_extraction from provided articles to highlight foundational divergences.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "Mathematical Formalism",
      "description": "Develops the mathematical structures of inductive biases, building on axioms to formalize how they influence learning, using pdf_deep_extract for equations from research papers.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n6",
      "level": 2,
      "title": "Formal Representation of Biases",
      "description": "Presents mathematical models like Bayesian priors for biases, explaining why formalism diverges from intuition in capturing generalization, with academic_search for relevant theorems.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n6",
      "level": 2,
      "title": "Equations for Bias in Neural Networks",
      "description": "Derives equations showing how biases affect weight updates, using code_search to pull pseudocode from implementations and highlight formal-intuition gaps.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n6",
      "level": 2,
      "title": "Impact on Optimization Landscapes",
      "description": "Formalizes how biases alter loss surfaces, with evidence from dataset_search on simulated experiments, emphasizing why this matters for learning dynamics.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n6",
      "level": 2,
      "title": "Divergence in Formal and Intuitive Models",
      "description": "Analyzes where mathematical formalism and intuitive understanding part ways, such as in non-convex optimization, using book_search for critiques from AI theory.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n6",
      "level": 2,
      "title": "Proofs of Bias Stability",
      "description": "Provides proofs for the stability of inductive biases under perturbations, drawing from academic_search to underscore first-principles necessity.",
      "section_type": "section"
    },
    {
      "node_id": "n12",
      "parent_id": "n1",
      "level": 1,
      "title": "Properties and Proofs",
      "description": "Explores properties of inductive biases through rigorous proofs, revealing why certain biases lead to incorrect generalizations, using patent_search for validated theoretical frameworks.",
      "section_type": "chapter"
    },
    {
      "node_id": "n13",
      "parent_id": "n12",
      "level": 2,
      "title": "Key Properties of Incorrect Biases",
      "description": "Details properties like brittleness and overfitting tendencies, with proofs from academic_search showing their derivation from core axioms.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n12",
      "level": 2,
      "title": "Proofs of Generalization Failure",
      "description": "Offers mathematical proofs demonstrating why incorrect biases fail to generalize, using video_search from the provided talk for illustrative derivations.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n12",
      "level": 2,
      "title": "Edge Cases in Bias Properties",
      "description": "Examines edge cases where biases amplify errors, with evidence from dataset_search on vision and language domains, including implementation considerations.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n12",
      "level": 2,
      "title": "Validation of Proofs Through Simulations",
      "description": "Validates theoretical proofs with simulated experiments, using code_search for scripts that test bias properties in controlled settings.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n12",
      "level": 2,
      "title": "Divergence in Proof Assumptions",
      "description": "Analyzes why proof assumptions sometimes diverge from real-world intuitions, drawing from forum_search discussions on AI limitations.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n1",
      "level": 1,
      "title": "Incorrect Inductive Biases in Domains",
      "description": "Applies foundational theory to identify and prove incorrect biases in specific domains, ensuring conceptual depth before examples.",
      "section_type": "chapter"
    },
    {
      "node_id": "n19",
      "parent_id": "n18",
      "level": 2,
      "title": "Vision Domain Biases",
      "description": "Identifies biases like background dependencies, with proofs of their incorrectness from academic_search, preparing for later experimental validation.",
      "section_type": "section"
    },
    {
      "node_id": "n20",
      "parent_id": "n18",
      "level": 2,
      "title": "Language Domain Biases",
      "description": "Explores biases in token embeddings, proving their failure in generalization using dataset_search for linguistic corpora.",
      "section_type": "section"
    },
    {
      "node_id": "n21",
      "parent_id": "n18",
      "level": 2,
      "title": "Cross-Domain Bias Interactions",
      "description": "Proves how biases transfer across domains, with evidence from web_search on multi-modal learning failures.",
      "section_type": "section"
    },
    {
      "node_id": "n22",
      "parent_id": "n18",
      "level": 2,
      "title": "Experimental Design for Bias Illustration",
      "description": "Outlines experiments to illustrate biases, using news_archive for real-world case studies, balanced with theoretical grounding.",
      "section_type": "section"
    },
    {
      "node_id": "n23",
      "parent_id": "n1",
      "level": 1,
      "title": "Addressing Inductive Biases",
      "description": "Transitions to solutions by proving methods to mitigate biases, drawing from established literature before suggesting innovations.",
      "section_type": "chapter"
    },
    {
      "node_id": "n24",
      "parent_id": "n23",
      "level": 2,
      "title": "Literature-Based Solutions",
      "description": "Reviews solutions like regularization techniques, with proofs of their effectiveness from academic_search, including implementation details.",
      "section_type": "section"
    },
    {
      "node_id": "n25",
      "parent_id": "n23",
      "level": 2,
      "title": "Validation of Mitigation Strategies",
      "description": "Provides edge-case validations for bias correction, using dataset_search for experimental data on various domains.",
      "section_type": "section"
    },
    {
      "node_id": "n26",
      "parent_id": "n23",
      "level": 2,
      "title": "Proposed New Method for Bias Reduction",
      "description": "Suggests a novel hybrid approach combining priors and adversarial training, with rationale from first-principles and code_search for prototypes.",
      "section_type": "section"
    },
    {
      "node_id": "n27",
      "parent_id": "n26",
      "level": 3,
      "title": "Step-by-Step Implementation",
      "description": "Details the implementation steps of the proposed method, including code snippets from code_search and validation tests for practitioners.",
      "section_type": "subsection"
    },
    {
      "node_id": "n28",
      "parent_id": "n23",
      "level": 2,
      "title": "Comparative Proofs of Solutions",
      "description": "Compares solution efficacy through proofs, using patent_search for patented techniques and highlighting divergence from intuitive fixes.",
      "section_type": "section"
    },
    {
      "node_id": "n29",
      "parent_id": "n28",
      "level": 3,
      "title": "Edge Case Analysis",
      "description": "Analyzes edge cases in solution proofs, with evidence from social_search on practitioner forums to ensure practical relevance.",
      "section_type": "subsection"
    }
  ]
}
```

