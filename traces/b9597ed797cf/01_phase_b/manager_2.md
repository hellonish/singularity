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

query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method. Report Describing your Approach for Realizing the Project
strength_context: target_section_count=19
available_retrieval_skills: dataset_search, patent_search, gov_search, social_search, book_search, data_extraction, standards_search, financial_search, web_search, pdf_deep_extract, video_search, forum_search, code_search, news_archive, clinical_search, legal_search, multimedia_search, academic_search
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

Produce exactly 19 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_2",
  "total_nodes": 19,
  "rationale": "This structure confronts practitioners with real-world problems of incorrect inductive biases first, introducing theory only as required to address those problems, enabling immediate application and progressive generalization.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Tackling Incorrect Inductive Biases in Deep Learning Through Problem-Driven Exploration",
      "description": "This report frames the investigation by starting with practical problems in deep learning where models fail to generalize due to flawed biases, using worked examples to guide the introduction of theory, generalization, and solutions, drawing on academic_search and dataset_search for evidence.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "The Apple-Orange Worked Example: A Core Problem of Background Bias",
      "description": "Present a concrete problem where a deep learning model incorrectly learns to classify fruits based on background colors instead of features, using dataset_search to fetch experimental datasets and video_search for illustrative clips, then introduce only the minimal theory needed for analysis.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Setting Up the Experiment",
      "description": "Detail the practical setup of the apple-orange classification task with biased backgrounds, using dataset_search to retrieve vision datasets and code_search for implementation scripts, focusing on edge cases like varying backgrounds to show failure modes.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Analyzing Model Failure",
      "description": "Examine how the bias leads to poor generalization through validation experiments, employing data_extraction on training logs and academic_search for related case studies, highlighting implementation pitfalls for practitioners.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n2",
      "level": 2,
      "title": "Introducing Essential Theory for This Bias",
      "description": "Introduce the minimum neural network theory required to understand shortcut learning, using book_search for foundational texts and academic_search for key papers, applied directly to fix the apple-orange problem.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n2",
      "level": 2,
      "title": "Initial Generalization Attempts",
      "description": "Explore basic ways to generalize from this problem by testing modified datasets, utilizing dataset_search for variants and forum_search for practitioner discussions on common fixes.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n1",
      "level": 1,
      "title": "New Problems in Vision Domains",
      "description": "Address emerging issues like texture bias in image recognition, building on the initial theory, with dataset_search for vision experiments and academic_search for evidence, focusing on implementation and validation.",
      "section_type": "chapter"
    },
    {
      "node_id": "n8",
      "parent_id": "n7",
      "level": 2,
      "title": "Experimenting with Texture Over Shape Bias",
      "description": "Run experiments showing models prioritizing textures over shapes, using dataset_search for image sets and code_search for training code, including edge cases like occluded objects.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n7",
      "level": 2,
      "title": "Extending Theory to Multi-Modal Biases",
      "description": "Introduce theory for handling multi-modal inputs as needed for these problems, drawing from academic_search and pdf_deep_extract of research papers, with a focus on practical validation techniques.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n7",
      "level": 2,
      "title": "Generalizing to Other Vision Tasks",
      "description": "Identify new problems like adversarial examples, using web_search for recent implementations and standards_search for benchmarking, to push theory further.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n1",
      "level": 1,
      "title": "Challenges in Language Domains",
      "description": "Tackle problems such as positional bias in NLP, extending from prior theory, with academic_search for language datasets and forum_search for real-world practitioner reports.",
      "section_type": "chapter"
    },
    {
      "node_id": "n12",
      "parent_id": "n11",
      "level": 2,
      "title": "Illustrating Positional Bias Experiments",
      "description": "Conduct experiments on text classification where models overfit to word positions, using dataset_search for NLP corpora and code_search for model scripts, including validation against edge cases.",
      "section_type": "section"
    },
    {
      "node_id": "n13",
      "parent_id": "n11",
      "level": 2,
      "title": "Refining Theory for Sequence Biases",
      "description": "Add theory on sequence modeling as required by these experiments, sourced from book_search and academic_search, with emphasis on implementation strategies.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n11",
      "level": 2,
      "title": "New Problems from Language Generalization",
      "description": "Explore issues like out-of-vocabulary biases, using web_search for examples and news_archive for contextual evidence, forcing further theoretical adaptation.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n11",
      "level": 2,
      "title": "Subsection: Edge Case Validation in NLP",
      "description": "Break down specific edge cases like rare words in real deployments, using dataset_search for targeted data and legal_search for compliance-related biases, as a detailed sub-argument.",
      "section_type": "subsection"
    },
    {
      "node_id": "n16",
      "parent_id": "n1",
      "level": 1,
      "title": "Solutions to Incorrect Inductive Biases",
      "description": "Address the accumulated problems by applying solutions, starting with literature methods then proposing new ones, using academic_search for evidence and patent_search for innovative approaches.",
      "section_type": "chapter"
    },
    {
      "node_id": "n17",
      "parent_id": "n16",
      "level": 2,
      "title": "Literature-Based Fixes",
      "description": "Review established solutions like data augmentation, with academic_search for papers and dataset_search for implementation examples, including validation metrics.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n16",
      "level": 2,
      "title": "Proposing a New Method",
      "description": "Suggest an original approach combining adversarial training with domain adaptation, using code_search for prototypes and forum_search for feedback, tailored for practitioner use.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n18",
      "level": 3,
      "title": "Testing the New Method",
      "description": "Detail experiments to validate the proposed method across domains, employing dataset_search for test sets and video_search for demonstrations, focusing on practical edge cases.",
      "section_type": "subsection"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_2",
  "rationale": "This structure confronts practitioners with real-world problems of incorrect inductive biases first, introducing theory only as required to address those problems, enabling immediate application and progressive generalization.",
  "total_nodes": 19,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Tackling Incorrect Inductive Biases in Deep Learning Through Problem-Driven Exploration",
      "description": "This report frames the investigation by starting with practical problems in deep learning where models fail to generalize due to flawed biases, using worked examples to guide the introduction of theory, generalization, and solutions, drawing on academic_search and dataset_search for evidence.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "The Apple-Orange Worked Example: A Core Problem of Background Bias",
      "description": "Present a concrete problem where a deep learning model incorrectly learns to classify fruits based on background colors instead of features, using dataset_search to fetch experimental datasets and video_search for illustrative clips, then introduce only the minimal theory needed for analysis.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Setting Up the Experiment",
      "description": "Detail the practical setup of the apple-orange classification task with biased backgrounds, using dataset_search to retrieve vision datasets and code_search for implementation scripts, focusing on edge cases like varying backgrounds to show failure modes.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Analyzing Model Failure",
      "description": "Examine how the bias leads to poor generalization through validation experiments, employing data_extraction on training logs and academic_search for related case studies, highlighting implementation pitfalls for practitioners.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n2",
      "level": 2,
      "title": "Introducing Essential Theory for This Bias",
      "description": "Introduce the minimum neural network theory required to understand shortcut learning, using book_search for foundational texts and academic_search for key papers, applied directly to fix the apple-orange problem.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n2",
      "level": 2,
      "title": "Initial Generalization Attempts",
      "description": "Explore basic ways to generalize from this problem by testing modified datasets, utilizing dataset_search for variants and forum_search for practitioner discussions on common fixes.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n1",
      "level": 1,
      "title": "New Problems in Vision Domains",
      "description": "Address emerging issues like texture bias in image recognition, building on the initial theory, with dataset_search for vision experiments and academic_search for evidence, focusing on implementation and validation.",
      "section_type": "chapter"
    },
    {
      "node_id": "n8",
      "parent_id": "n7",
      "level": 2,
      "title": "Experimenting with Texture Over Shape Bias",
      "description": "Run experiments showing models prioritizing textures over shapes, using dataset_search for image sets and code_search for training code, including edge cases like occluded objects.",
      "section_type": "section"
    },
    {
      "node_id": "n9",
      "parent_id": "n7",
      "level": 2,
      "title": "Extending Theory to Multi-Modal Biases",
      "description": "Introduce theory for handling multi-modal inputs as needed for these problems, drawing from academic_search and pdf_deep_extract of research papers, with a focus on practical validation techniques.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n7",
      "level": 2,
      "title": "Generalizing to Other Vision Tasks",
      "description": "Identify new problems like adversarial examples, using web_search for recent implementations and standards_search for benchmarking, to push theory further.",
      "section_type": "section"
    },
    {
      "node_id": "n11",
      "parent_id": "n1",
      "level": 1,
      "title": "Challenges in Language Domains",
      "description": "Tackle problems such as positional bias in NLP, extending from prior theory, with academic_search for language datasets and forum_search for real-world practitioner reports.",
      "section_type": "chapter"
    },
    {
      "node_id": "n12",
      "parent_id": "n11",
      "level": 2,
      "title": "Illustrating Positional Bias Experiments",
      "description": "Conduct experiments on text classification where models overfit to word positions, using dataset_search for NLP corpora and code_search for model scripts, including validation against edge cases.",
      "section_type": "section"
    },
    {
      "node_id": "n13",
      "parent_id": "n11",
      "level": 2,
      "title": "Refining Theory for Sequence Biases",
      "description": "Add theory on sequence modeling as required by these experiments, sourced from book_search and academic_search, with emphasis on implementation strategies.",
      "section_type": "section"
    },
    {
      "node_id": "n14",
      "parent_id": "n11",
      "level": 2,
      "title": "New Problems from Language Generalization",
      "description": "Explore issues like out-of-vocabulary biases, using web_search for examples and news_archive for contextual evidence, forcing further theoretical adaptation.",
      "section_type": "section"
    },
    {
      "node_id": "n15",
      "parent_id": "n11",
      "level": 2,
      "title": "Subsection: Edge Case Validation in NLP",
      "description": "Break down specific edge cases like rare words in real deployments, using dataset_search for targeted data and legal_search for compliance-related biases, as a detailed sub-argument.",
      "section_type": "subsection"
    },
    {
      "node_id": "n16",
      "parent_id": "n1",
      "level": 1,
      "title": "Solutions to Incorrect Inductive Biases",
      "description": "Address the accumulated problems by applying solutions, starting with literature methods then proposing new ones, using academic_search for evidence and patent_search for innovative approaches.",
      "section_type": "chapter"
    },
    {
      "node_id": "n17",
      "parent_id": "n16",
      "level": 2,
      "title": "Literature-Based Fixes",
      "description": "Review established solutions like data augmentation, with academic_search for papers and dataset_search for implementation examples, including validation metrics.",
      "section_type": "section"
    },
    {
      "node_id": "n18",
      "parent_id": "n16",
      "level": 2,
      "title": "Proposing a New Method",
      "description": "Suggest an original approach combining adversarial training with domain adaptation, using code_search for prototypes and forum_search for feedback, tailored for practitioner use.",
      "section_type": "section"
    },
    {
      "node_id": "n19",
      "parent_id": "n18",
      "level": 3,
      "title": "Testing the New Method",
      "description": "Detail experiments to validate the proposed method across domains, employing dataset_search for test sets and video_search for demonstrations, focusing on practical edge cases.",
      "section_type": "subsection"
    }
  ]
}
```

