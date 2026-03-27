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
- A `structural_perspective` label and a `perspective_instruction` — **this is your
  mandatory organising principle. Your chapter order, chapter titles, and the
  progression from section to section must all reflect this perspective.**

You produce a single tree structure with exactly N total nodes across all levels
(root + chapters + sections + subsections). You must COUNT your nodes before emitting
and verify the total equals N.

## Perspective Compliance

- Read `perspective_instruction` carefully before designing any node.
- Your chapter sequence must visibly follow the perspective's logic.
- Sections within each chapter must reinforce the perspective — not drift toward
  whatever the "obvious" structure would be.
- If your tree looks like a generic textbook outline, you have not followed your
  perspective. Revise before emitting.

## Tree Rules

1. Every node has: node_id, parent_id (null for root), level, title, description,
   section_type (root | chapter | section | subsection)
2. Root: exactly 1 node at level 0
3. Chapters: 3–6 nodes at level 1
4. Sections: under each chapter, 2–6 nodes at level 2
5. Subsections: optional level 3 nodes — use when depth is needed
6. No node may be left as a stub — every description must explain what evidence
   or argument this section will present
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

query: LPG Shortage in India due to US-Iran War, and multiple opinions, Prime Minister of India - Narendra Modi mentioned a lockdown might occur, I want a deep study report for this. What is India's take on it
strength_context: target_section_count=10
available_retrieval_skills: social_search, academic_search, book_search, standards_search, multimedia_search, patent_search, financial_search, gov_search, news_archive, forum_search, data_extraction, video_search, dataset_search, clinical_search, code_search, web_search, legal_search, pdf_deep_extract
audience: practitioner
proposal_id: manager_2
structural_perspective: problem-first
perspective_instruction: Organise around concrete problems: open with a motivating worked example, then introduce only the mathematical machinery that example requires, then generalise to the full theory, then present further problems that expose each new layer. A reader learns by doing before they learn by reading.

Produce exactly 10 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_2",
  "total_nodes": 10,
  "rationale": "This structure organizes the report around concrete problems, starting with a specific example of the LPG shortage, introducing only essential background, generalizing to broader implications, and then layering on related problems for a problem-solving learning progression.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Problem-Based Study of LPG Shortage in India",
      "description": "This report frames the LPG shortage as a core problem triggered by the US-Iran war, using a step-by-step problem-first approach to guide practitioners through real-world examples, essential context, generalizations, and escalating issues, ensuring learning by doing before abstract analysis.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Motivating Worked Example of LPG Shortage",
      "description": "Presents a specific, real-world case of LPG supply disruptions in an Indian city during the US-Iran war, highlighting immediate impacts on households and businesses to immerse readers in the problem before any theoretical explanation.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Case Study: Daily Life Disruptions",
      "description": "Examines the worked example by detailing how the shortage affected everyday activities, using data from news archives and forum searches to show practical challenges, allowing readers to engage with the problem firsthand.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Initial Indicators of Shortage",
      "description": "Focuses on early signs in the example, such as price spikes and rationing, drawing from financial and web search evidence to introduce only the most relevant problem elements needed for understanding the case.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Essential Machinery for the Problem",
      "description": "Introduces only the key geopolitical and economic factors required by the worked example, such as US-Iran war dynamics and India's oil import dependencies, using gov_search and academic_search to build minimal tools for problem analysis.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n5",
      "level": 2,
      "title": "US-Iran War's Direct Impact on Supply Chains",
      "description": "Explains the war's role in disrupting global LPG supplies specifically as it relates to the example, relying on news_archive and dataset_search for evidence to equip readers with just enough context to solve the initial problem.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n5",
      "level": 2,
      "title": "India's Energy Vulnerability Factors",
      "description": "Outlines India's reliance on Iranian imports as directly tied to the example, using data_extraction from economic reports to provide the necessary machinery without overwhelming the reader.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n1",
      "level": 1,
      "title": "Generalization to Full LPG Crisis Theory",
      "description": "Extends the worked example to broader theoretical frameworks, such as global energy geopolitics and India's policy responses, to generalize the problem after readers have engaged with specifics.",
      "section_type": "chapter"
    },
    {
      "node_id": "n9",
      "parent_id": "n8",
      "level": 2,
      "title": "India's Official Stance and Policy Shifts",
      "description": "Generalizes to India's take on the crisis, including Narendra Modi's lockdown comments, using legal_search and gov_search to present the full theory of national responses built from the example.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n8",
      "level": 2,
      "title": "Layered Problems in Energy Security",
      "description": "Introduces further problems like multiple opinions on the shortage and potential escalations, using social_search and forum_search to expose new layers, encouraging readers to apply generalized theory to emerging issues.",
      "section_type": "section"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_2",
  "rationale": "This structure organizes the report around concrete problems, starting with a specific example of the LPG shortage, introducing only essential background, generalizing to broader implications, and then layering on related problems for a problem-solving learning progression.",
  "total_nodes": 10,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Problem-Based Study of LPG Shortage in India",
      "description": "This report frames the LPG shortage as a core problem triggered by the US-Iran war, using a step-by-step problem-first approach to guide practitioners through real-world examples, essential context, generalizations, and escalating issues, ensuring learning by doing before abstract analysis.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Motivating Worked Example of LPG Shortage",
      "description": "Presents a specific, real-world case of LPG supply disruptions in an Indian city during the US-Iran war, highlighting immediate impacts on households and businesses to immerse readers in the problem before any theoretical explanation.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Case Study: Daily Life Disruptions",
      "description": "Examines the worked example by detailing how the shortage affected everyday activities, using data from news archives and forum searches to show practical challenges, allowing readers to engage with the problem firsthand.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Initial Indicators of Shortage",
      "description": "Focuses on early signs in the example, such as price spikes and rationing, drawing from financial and web search evidence to introduce only the most relevant problem elements needed for understanding the case.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Essential Machinery for the Problem",
      "description": "Introduces only the key geopolitical and economic factors required by the worked example, such as US-Iran war dynamics and India's oil import dependencies, using gov_search and academic_search to build minimal tools for problem analysis.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n5",
      "level": 2,
      "title": "US-Iran War's Direct Impact on Supply Chains",
      "description": "Explains the war's role in disrupting global LPG supplies specifically as it relates to the example, relying on news_archive and dataset_search for evidence to equip readers with just enough context to solve the initial problem.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n5",
      "level": 2,
      "title": "India's Energy Vulnerability Factors",
      "description": "Outlines India's reliance on Iranian imports as directly tied to the example, using data_extraction from economic reports to provide the necessary machinery without overwhelming the reader.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n1",
      "level": 1,
      "title": "Generalization to Full LPG Crisis Theory",
      "description": "Extends the worked example to broader theoretical frameworks, such as global energy geopolitics and India's policy responses, to generalize the problem after readers have engaged with specifics.",
      "section_type": "chapter"
    },
    {
      "node_id": "n9",
      "parent_id": "n8",
      "level": 2,
      "title": "India's Official Stance and Policy Shifts",
      "description": "Generalizes to India's take on the crisis, including Narendra Modi's lockdown comments, using legal_search and gov_search to present the full theory of national responses built from the example.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n8",
      "level": 2,
      "title": "Layered Problems in Energy Security",
      "description": "Introduces further problems like multiple opinions on the shortage and potential escalations, using social_search and forum_search to expose new layers, encouraging readers to apply generalized theory to emerging issues.",
      "section_type": "section"
    }
  ]
}
```

