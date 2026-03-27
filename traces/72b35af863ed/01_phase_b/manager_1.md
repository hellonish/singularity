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
proposal_id: manager_1
structural_perspective: concept-first
perspective_instruction: Organise from foundational theory outward: start with definitions and axioms, build through mathematical formalism, then move to properties, proofs, and finally real-world applications. A reader should understand the 'why' deeply before encountering any worked examples.

Produce exactly 10 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_1",
  "total_nodes": 10,
  "rationale": "This structure begins with core conceptual foundations to build deep theoretical understanding before progressing to formal analyses and real-world applications, ensuring readers grasp the 'why' underlying the LPG shortage in India.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Foundational Analysis of LPG Shortage in India Amid US-Iran Tensions",
      "description": "This report frames the LPG shortage as a geopolitical-economic issue, starting from basic definitions and axioms to progressively build toward formal models and real-world applications, emphasizing India's perspective through evidence from news archives and government sources.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Definitions and Axioms of Global Energy Supply",
      "description": "Establishes foundational concepts by defining LPG, its role in India's energy framework, and axioms of international oil trade disruptions, drawing on academic_search and book_search for theoretical underpinnings.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Defining LPG and Its Economic Axioms",
      "description": "Explores the basic definition of LPG as a resource and its axiomatic principles in global markets, using standards_search to outline supply chain axioms and prepare for deeper analysis.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Axioms of Geopolitical Disruptions",
      "description": "Outlines axioms related to conflicts like the US-Iran War affecting energy supplies, leveraging historical data from news_archive to establish why such events inherently disrupt flows.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Mathematical Formalism of Energy Market Dynamics",
      "description": "Builds on foundations by introducing mathematical models of supply and demand, focusing on formal economic equations for energy shortages, informed by financial_search and dataset_search.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n5",
      "level": 2,
      "title": "Formal Models of Supply Chain Interruptions",
      "description": "Presents mathematical formalisms like network flow models for oil supply chains, proving how US-Iran tensions mathematically propagate shortages to India via equations and simulations.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n5",
      "level": 2,
      "title": "Equations for Economic Impact Assessment",
      "description": "Develops formal equations to quantify LPG price fluctuations and scarcity, using data_extraction to derive proofs of economic axioms in the Indian context.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n1",
      "level": 1,
      "title": "Properties, Proofs, and Real-World Applications",
      "description": "Examines properties and proofs of the modeled disruptions before applying them to real-world scenarios, ensuring a logical transition from theory to India's governmental responses.",
      "section_type": "chapter"
    },
    {
      "node_id": "n9",
      "parent_id": "n8",
      "level": 2,
      "title": "Properties and Proofs of Shortage Impacts",
      "description": "Analyzes properties of energy crises, such as cascading effects on Indian households, with proofs linking US-Iran War axioms to local shortages via gov_search evidence.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n8",
      "level": 2,
      "title": "Real-World Applications and Indian Perspectives",
      "description": "Applies proven models to Narendra Modi's lockdown statements and multiple opinions, using forum_search and video_search to explore India's strategies and policy responses.",
      "section_type": "section"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_1",
  "rationale": "This structure begins with core conceptual foundations to build deep theoretical understanding before progressing to formal analyses and real-world applications, ensuring readers grasp the 'why' underlying the LPG shortage in India.",
  "total_nodes": 10,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Foundational Analysis of LPG Shortage in India Amid US-Iran Tensions",
      "description": "This report frames the LPG shortage as a geopolitical-economic issue, starting from basic definitions and axioms to progressively build toward formal models and real-world applications, emphasizing India's perspective through evidence from news archives and government sources.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Definitions and Axioms of Global Energy Supply",
      "description": "Establishes foundational concepts by defining LPG, its role in India's energy framework, and axioms of international oil trade disruptions, drawing on academic_search and book_search for theoretical underpinnings.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Defining LPG and Its Economic Axioms",
      "description": "Explores the basic definition of LPG as a resource and its axiomatic principles in global markets, using standards_search to outline supply chain axioms and prepare for deeper analysis.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Axioms of Geopolitical Disruptions",
      "description": "Outlines axioms related to conflicts like the US-Iran War affecting energy supplies, leveraging historical data from news_archive to establish why such events inherently disrupt flows.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Mathematical Formalism of Energy Market Dynamics",
      "description": "Builds on foundations by introducing mathematical models of supply and demand, focusing on formal economic equations for energy shortages, informed by financial_search and dataset_search.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n5",
      "level": 2,
      "title": "Formal Models of Supply Chain Interruptions",
      "description": "Presents mathematical formalisms like network flow models for oil supply chains, proving how US-Iran tensions mathematically propagate shortages to India via equations and simulations.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n5",
      "level": 2,
      "title": "Equations for Economic Impact Assessment",
      "description": "Develops formal equations to quantify LPG price fluctuations and scarcity, using data_extraction to derive proofs of economic axioms in the Indian context.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n1",
      "level": 1,
      "title": "Properties, Proofs, and Real-World Applications",
      "description": "Examines properties and proofs of the modeled disruptions before applying them to real-world scenarios, ensuring a logical transition from theory to India's governmental responses.",
      "section_type": "chapter"
    },
    {
      "node_id": "n9",
      "parent_id": "n8",
      "level": 2,
      "title": "Properties and Proofs of Shortage Impacts",
      "description": "Analyzes properties of energy crises, such as cascading effects on Indian households, with proofs linking US-Iran War axioms to local shortages via gov_search evidence.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n8",
      "level": 2,
      "title": "Real-World Applications and Indian Perspectives",
      "description": "Applies proven models to Narendra Modi's lockdown statements and multiple opinions, using forum_search and video_search to explore India's strategies and policy responses.",
      "section_type": "section"
    }
  ]
}
```

