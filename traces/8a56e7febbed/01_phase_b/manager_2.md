# Manager 2 — Report Structure Proposal

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
proposal_id: manager_2
structural_perspective: problem-first
perspective_instruction:
ROLE: You are a pedagogy-first architect. Your structure leads with difficulty: the reader is immediately confronted with a real problem and acquires theory only as it becomes necessary to solve what they are already working on.

STRUCTURE PRINCIPLE: Organise around concrete problems: open with a motivating worked example, then introduce only the mathematical machinery that example requires, then generalise to the full theory, then present further problems that expose each new layer. A reader learns by doing before they learn by reading.

KEY QUESTIONS — your tree must answer these:
  - What is the single most clarifying worked example — the one that makes everything click?
  - What is the minimum theory needed to solve the first problem — and nothing more?
  - What new problems appear as capability grows, forcing the theory to generalise?

ANTI-PATTERNS — explicitly avoid:
  ✗ Do NOT begin with definitions or axioms — begin with a problem the reader can feel.
  ✗ Do NOT introduce mathematical machinery before the need for it is concrete.
  ✗ Do NOT use 'in general' as a chapter opener — save generalisation for after worked problems.

Produce exactly 29 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_2",
  "total_nodes": 29,
  "rationale": "This structure organizes the report by confronting practitioners with real-world problems of incorrect inductive biases first, introducing theory only as necessary to solve them, and then building to generalizations and solutions.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Tackling Incorrect Inductive Biases in Deep Learning Through Problem-Driven Exploration",
      "description": "This report frames incorrect inductive biases as practical challenges in model generalization, starting with concrete problems to engage practitioners, and progressing to theory and solutions as needed, using retrieval skills like dataset_search for experiments and academic_search for validations.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Initial Problem: Background Color Bias in Fruit Classification",
      "description": "Present the core worked example of a deep learning model confusing background colors with fruit types, forcing practitioners to confront this real issue immediately, using dataset_search to fetch vision datasets for illustration and video_search for related demonstrations.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n1",
      "level": 1,
      "title": "Minimum Theory for Solving the Initial Bias",
      "description": "Introduce only the essential concepts needed to address the background color problem, such as basic inductive bias definitions through implementation, using academic_search for targeted papers and code_search for simple model tweaks.",
      "section_type": "chapter"
    },
    {
      "node_id": "n4",
      "parent_id": "n1",
      "level": 1,
      "title": "New Problems Emerging from Basic Solutions",
      "description": "Explore additional biases that arise when applying initial fixes, like positional biases in language models, to generalize from the first problem, employing dataset_search for new experimental setups and forum_search for practitioner-reported edge cases.",
      "section_type": "chapter"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Literature-Based Solutions to Identified Biases",
      "description": "Address the new problems by presenting established methods from research, focusing on practical implementations, using academic_search for key papers and patent_search for applied techniques.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "Innovative Approaches and Validation",
      "description": "Propose original methods and validate them against the problems, ensuring practitioners can apply and test solutions, with code_search for prototypes and data_extraction for experimental results.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n2",
      "level": 2,
      "title": "Replicating the Fruit Classification Experiment",
      "description": "Detail the step-by-step replication of the background color bias using a simple vision dataset, including edge cases like varied lighting, and use dataset_search to retrieve specific image sets for hands-on implementation.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n2",
      "level": 2,
      "title": "Measuring Generalization Failure",
      "description": "Examine how the model fails on unseen data, quantifying bias impact through metrics, and employ data_extraction to analyze outputs from the experiment.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n2",
      "level": 2,
      "title": "Initial Observations from the Problem",
      "description": "Discuss practitioner insights from the worked example, such as common pitfalls in data setup, using forum_search for real-world anecdotes to highlight immediate challenges.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n3",
      "level": 2,
      "title": "Core Mechanisms of Inductive Bias",
      "description": "Break down the minimal theory behind why biases occur, focusing on neural network architectures, and use academic_search for foundational references to support problem-solving.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n3",
      "level": 2,
      "title": "Implementing Bias Detection in Code",
      "description": "Provide code-level steps to detect biases in the fruit example, including validation techniques, leveraging code_search for snippets and pdf_deep_extract for detailed algorithms.",
      "section_type": "section"
    },
    {
      "node_id": "n12",
      "parent_id": "n3",
      "level": 2,
      "title": "Edge Cases in Bias Application",
      "description": "Address practical edge cases like noisy data that arise in implementation, using dataset_search to simulate variations.",
      "section_type": "section"
    },
    {
      "node_id": "n13",
      "parent_id": "n3",
      "level": 2,
      "title": "Validation of Initial Theory",
      "description": "Validate the theory through quick experiments on the original problem, employing web_search for comparative studies.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n4",
      "level": 2,
      "title": "Positional Bias in Language Models",
      "description": "Introduce a new problem where models over-rely on word positions, emerging from solving the initial bias, and use dataset_search for language corpora to run tests.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n4",
      "level": 2,
      "title": "Shortcut Learning in Vision Tasks",
      "description": "Examine how models exploit unintended features, forcing theory generalization, with multimedia_search for vision examples.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n4",
      "level": 2,
      "title": "Generalization Challenges Across Domains",
      "description": "Discuss domain-specific problems like in NLP versus CV, using academic_search to identify patterns.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n4",
      "level": 2,
      "title": "Experimental Setup for New Biases",
      "description": "Outline experiments to expose these biases, including implementation details, and leverage video_search for illustrative demos.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n4",
      "level": 2,
      "title": "Quantifying Impact on Model Performance",
      "description": "Measure how these problems affect real-world applications, using data_extraction for performance metrics.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n5",
      "level": 2,
      "title": "Data Augmentation Techniques",
      "description": "Present literature solutions like data augmentation to counter biases, with practical implementation steps, drawing from academic_search for case studies.",
      "section_type": "section"
    },
    {
      "node_id": "n20",
      "parent_id": "n5",
      "level": 2,
      "title": "Regularization Methods",
      "description": "Discuss regularization as a solution, including code examples, and use book_search for theoretical backing.",
      "section_type": "section"
    },
    {
      "node_id": "n21",
      "parent_id": "n5",
      "level": 2,
      "title": "Adversarial Training Approaches",
      "description": "Explore adversarial methods from literature, focusing on validation, with patent_search for innovative applications.",
      "section_type": "section"
    },
    {
      "node_id": "n22",
      "parent_id": "n5",
      "level": 2,
      "title": "Evaluation of Solution Effectiveness",
      "description": "Validate these solutions through experiments, using dataset_search for comparative data.",
      "section_type": "section"
    },
    {
      "node_id": "n23",
      "parent_id": "n6",
      "level": 2,
      "title": "Proposed Hybrid Data-Mixing Method",
      "description": "Suggest a new method combining datasets to address biases, with implementation guidelines, and use code_search for prototypes.",
      "section_type": "section"
    },
    {
      "node_id": "n24",
      "parent_id": "n6",
      "level": 2,
      "title": "Bias-Aware Training Regimens",
      "description": "Outline a custom training approach, including edge cases, leveraging academic_search for inspiration.",
      "section_type": "section"
    },
    {
      "node_id": "n25",
      "parent_id": "n6",
      "level": 2,
      "title": "Validation Experiments for New Methods",
      "description": "Run experiments to test the proposed solutions, using data_extraction for results analysis.",
      "section_type": "section"
    },
    {
      "node_id": "n26",
      "parent_id": "n7",
      "level": 3,
      "title": "Step-by-Step Data Preparation",
      "description": "Break down the data setup for the fruit experiment, including specific tools and checks, with dataset_search providing the raw data.",
      "section_type": "subsection"
    },
    {
      "node_id": "n27",
      "parent_id": "n7",
      "level": 3,
      "title": "Model Training and Testing Protocol",
      "description": "Detail the exact training loop and evaluation steps for practitioners, using code_search for verified scripts.",
      "section_type": "subsection"
    },
    {
      "node_id": "n28",
      "parent_id": "n10",
      "level": 3,
      "title": "Key Architectural Influences",
      "description": "Examine how network layers contribute to biases, with academic_search for diagrams and examples.",
      "section_type": "subsection"
    },
    {
      "node_id": "n29",
      "parent_id": "n10",
      "level": 3,
      "title": "Practical Detection Algorithms",
      "description": "Provide algorithms for detecting biases in code, including validation, via code_search for implementations.",
      "section_type": "subsection"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_2",
  "rationale": "This structure organizes the report by confronting practitioners with real-world problems of incorrect inductive biases first, introducing theory only as necessary to solve them, and then building to generalizations and solutions.",
  "total_nodes": 29,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Tackling Incorrect Inductive Biases in Deep Learning Through Problem-Driven Exploration",
      "description": "This report frames incorrect inductive biases as practical challenges in model generalization, starting with concrete problems to engage practitioners, and progressing to theory and solutions as needed, using retrieval skills like dataset_search for experiments and academic_search for validations.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Initial Problem: Background Color Bias in Fruit Classification",
      "description": "Present the core worked example of a deep learning model confusing background colors with fruit types, forcing practitioners to confront this real issue immediately, using dataset_search to fetch vision datasets for illustration and video_search for related demonstrations.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n1",
      "level": 1,
      "title": "Minimum Theory for Solving the Initial Bias",
      "description": "Introduce only the essential concepts needed to address the background color problem, such as basic inductive bias definitions through implementation, using academic_search for targeted papers and code_search for simple model tweaks.",
      "section_type": "chapter"
    },
    {
      "node_id": "n4",
      "parent_id": "n1",
      "level": 1,
      "title": "New Problems Emerging from Basic Solutions",
      "description": "Explore additional biases that arise when applying initial fixes, like positional biases in language models, to generalize from the first problem, employing dataset_search for new experimental setups and forum_search for practitioner-reported edge cases.",
      "section_type": "chapter"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Literature-Based Solutions to Identified Biases",
      "description": "Address the new problems by presenting established methods from research, focusing on practical implementations, using academic_search for key papers and patent_search for applied techniques.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "Innovative Approaches and Validation",
      "description": "Propose original methods and validate them against the problems, ensuring practitioners can apply and test solutions, with code_search for prototypes and data_extraction for experimental results.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n2",
      "level": 2,
      "title": "Replicating the Fruit Classification Experiment",
      "description": "Detail the step-by-step replication of the background color bias using a simple vision dataset, including edge cases like varied lighting, and use dataset_search to retrieve specific image sets for hands-on implementation.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n2",
      "level": 2,
      "title": "Measuring Generalization Failure",
      "description": "Examine how the model fails on unseen data, quantifying bias impact through metrics, and employ data_extraction to analyze outputs from the experiment.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n2",
      "level": 2,
      "title": "Initial Observations from the Problem",
      "description": "Discuss practitioner insights from the worked example, such as common pitfalls in data setup, using forum_search for real-world anecdotes to highlight immediate challenges.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n3",
      "level": 2,
      "title": "Core Mechanisms of Inductive Bias",
      "description": "Break down the minimal theory behind why biases occur, focusing on neural network architectures, and use academic_search for foundational references to support problem-solving.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n3",
      "level": 2,
      "title": "Implementing Bias Detection in Code",
      "description": "Provide code-level steps to detect biases in the fruit example, including validation techniques, leveraging code_search for snippets and pdf_deep_extract for detailed algorithms.",
      "section_type": "section"
    },
    {
      "node_id": "n12",
      "parent_id": "n3",
      "level": 2,
      "title": "Edge Cases in Bias Application",
      "description": "Address practical edge cases like noisy data that arise in implementation, using dataset_search to simulate variations.",
      "section_type": "section"
    },
    {
      "node_id": "n13",
      "parent_id": "n3",
      "level": 2,
      "title": "Validation of Initial Theory",
      "description": "Validate the theory through quick experiments on the original problem, employing web_search for comparative studies.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n4",
      "level": 2,
      "title": "Positional Bias in Language Models",
      "description": "Introduce a new problem where models over-rely on word positions, emerging from solving the initial bias, and use dataset_search for language corpora to run tests.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n4",
      "level": 2,
      "title": "Shortcut Learning in Vision Tasks",
      "description": "Examine how models exploit unintended features, forcing theory generalization, with multimedia_search for vision examples.",
      "section_type": "section"
    },
    {
      "node_id": "n16",
      "parent_id": "n4",
      "level": 2,
      "title": "Generalization Challenges Across Domains",
      "description": "Discuss domain-specific problems like in NLP versus CV, using academic_search to identify patterns.",
      "section_type": "section"
    },
    {
      "node_id": "n17",
      "parent_id": "n4",
      "level": 2,
      "title": "Experimental Setup for New Biases",
      "description": "Outline experiments to expose these biases, including implementation details, and leverage video_search for illustrative demos.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n4",
      "level": 2,
      "title": "Quantifying Impact on Model Performance",
      "description": "Measure how these problems affect real-world applications, using data_extraction for performance metrics.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n5",
      "level": 2,
      "title": "Data Augmentation Techniques",
      "description": "Present literature solutions like data augmentation to counter biases, with practical implementation steps, drawing from academic_search for case studies.",
      "section_type": "section"
    },
    {
      "node_id": "n20",
      "parent_id": "n5",
      "level": 2,
      "title": "Regularization Methods",
      "description": "Discuss regularization as a solution, including code examples, and use book_search for theoretical backing.",
      "section_type": "section"
    },
    {
      "node_id": "n21",
      "parent_id": "n5",
      "level": 2,
      "title": "Adversarial Training Approaches",
      "description": "Explore adversarial methods from literature, focusing on validation, with patent_search for innovative applications.",
      "section_type": "section"
    },
    {
      "node_id": "n22",
      "parent_id": "n5",
      "level": 2,
      "title": "Evaluation of Solution Effectiveness",
      "description": "Validate these solutions through experiments, using dataset_search for comparative data.",
      "section_type": "section"
    },
    {
      "node_id": "n23",
      "parent_id": "n6",
      "level": 2,
      "title": "Proposed Hybrid Data-Mixing Method",
      "description": "Suggest a new method combining datasets to address biases, with implementation guidelines, and use code_search for prototypes.",
      "section_type": "section"
    },
    {
      "node_id": "n24",
      "parent_id": "n6",
      "level": 2,
      "title": "Bias-Aware Training Regimens",
      "description": "Outline a custom training approach, including edge cases, leveraging academic_search for inspiration.",
      "section_type": "section"
    },
    {
      "node_id": "n25",
      "parent_id": "n6",
      "level": 2,
      "title": "Validation Experiments for New Methods",
      "description": "Run experiments to test the proposed solutions, using data_extraction for results analysis.",
      "section_type": "section"
    },
    {
      "node_id": "n26",
      "parent_id": "n7",
      "level": 3,
      "title": "Step-by-Step Data Preparation",
      "description": "Break down the data setup for the fruit experiment, including specific tools and checks, with dataset_search providing the raw data.",
      "section_type": "subsection"
    },
    {
      "node_id": "n27",
      "parent_id": "n7",
      "level": 3,
      "title": "Model Training and Testing Protocol",
      "description": "Detail the exact training loop and evaluation steps for practitioners, using code_search for verified scripts.",
      "section_type": "subsection"
    },
    {
      "node_id": "n28",
      "parent_id": "n10",
      "level": 3,
      "title": "Key Architectural Influences",
      "description": "Examine how network layers contribute to biases, with academic_search for diagrams and examples.",
      "section_type": "subsection"
    },
    {
      "node_id": "n29",
      "parent_id": "n10",
      "level": 3,
      "title": "Practical Detection Algorithms",
      "description": "Provide algorithms for detecting biases in code, including validation, via code_search for implementations.",
      "section_type": "subsection"
    }
  ]
}
```

