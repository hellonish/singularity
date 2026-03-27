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
proposal_id: manager_3
structural_perspective: practitioner-workflow
perspective_instruction: Organise as a practitioner's guide: when and why to use this technique, step-by-step implementation with decision points, common edge cases and failure modes, validation strategies, and performance / complexity considerations. Theory appears only where it directly informs a decision.

Produce exactly 10 nodes. Count before emitting.

## Raw LLM Response

```
{
  "proposal_id": "manager_3",
  "total_nodes": 10,
  "rationale": "This structure organizes the report as a practitioner's workflow for managing LPG shortages, progressing from initial assessment to implementation and evaluation, with theory integrated only to inform decisions.",
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Practitioner's Guide to Managing LPG Shortages in Geopolitical Crises",
      "description": "This root frames the report as a step-by-step workflow for practitioners like energy analysts or policymakers to handle LPG supply disruptions, such as those from the US-Iran War, drawing on India's responses and using retrieval skills like news_archive and gov_search for real-world evidence.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Identifying When and Why to Intervene",
      "description": "This chapter outlines scenarios where practitioners should address LPG shortages, focusing on geopolitical triggers like the US-Iran War and India's official stances, using gov_search for Narendra Modi's statements and news_archive to evaluate risks and benefits.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Triggers for Immediate Analysis",
      "description": "This section details specific events, such as war-related supply cuts, that signal the need for action, incorporating data from news_archive and social_search to inform practitioners on timing decisions based on real-time indicators from India's energy sector.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Rationale for Strategic Responses",
      "description": "This section explains why practitioners should prioritize interventions, highlighting economic and social impacts like potential lockdowns mentioned by Modi, with evidence from academic_search to justify decisions without delving into unrelated theory.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Step-by-Step Implementation with Decision Points",
      "description": "This chapter provides a sequential guide for practitioners to implement shortage mitigation strategies, including decision points on resource allocation, using forum_search for practical insights and data_extraction to adapt India's approaches to local contexts.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n5",
      "level": 2,
      "title": "Core Steps for Supply Chain Adjustments",
      "description": "This section breaks down the implementation process, from assessing imports to domestic alternatives, with decision points informed by financial_search for cost analysis and web_search for current trade data related to India's LPG imports.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n5",
      "level": 2,
      "title": "Key Decision Points in Escalation",
      "description": "This section addresses choices like invoking lockdowns, using evidence from legal_search on India's policies and video_search for Modi's public addresses to guide practitioners on escalation based on shortage severity.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n1",
      "level": 1,
      "title": "Ensuring Effective Outcomes",
      "description": "This chapter covers handling uncertainties and validating strategies, focusing on practical performance metrics for practitioners monitoring LPG shortages, with dataset_search for impact data and standards_search for compliance checks.",
      "section_type": "chapter"
    },
    {
      "node_id": "n9",
      "parent_id": "n8",
      "level": 2,
      "title": "Managing Edge Cases and Failure Modes",
      "description": "This section identifies common pitfalls, such as prolonged wars exacerbating shortages, and strategies to mitigate them, drawing on historical data from news_archive to inform decisions on alternative energy sources in India's context.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n8",
      "level": 2,
      "title": "Validation and Performance Considerations",
      "description": "This section outlines methods to validate interventions and evaluate complexity, using performance metrics from financial_search and academic_search where it directly informs efficiency decisions for India's LPG management.",
      "section_type": "section"
    }
  ]
}
```

## Parsed Tree (JSON)

```json
{
  "proposal_id": "manager_3",
  "rationale": "This structure organizes the report as a practitioner's workflow for managing LPG shortages, progressing from initial assessment to implementation and evaluation, with theory integrated only to inform decisions.",
  "total_nodes": 10,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Practitioner's Guide to Managing LPG Shortages in Geopolitical Crises",
      "description": "This root frames the report as a step-by-step workflow for practitioners like energy analysts or policymakers to handle LPG supply disruptions, such as those from the US-Iran War, drawing on India's responses and using retrieval skills like news_archive and gov_search for real-world evidence.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Identifying When and Why to Intervene",
      "description": "This chapter outlines scenarios where practitioners should address LPG shortages, focusing on geopolitical triggers like the US-Iran War and India's official stances, using gov_search for Narendra Modi's statements and news_archive to evaluate risks and benefits.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Triggers for Immediate Analysis",
      "description": "This section details specific events, such as war-related supply cuts, that signal the need for action, incorporating data from news_archive and social_search to inform practitioners on timing decisions based on real-time indicators from India's energy sector.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n2",
      "level": 2,
      "title": "Rationale for Strategic Responses",
      "description": "This section explains why practitioners should prioritize interventions, highlighting economic and social impacts like potential lockdowns mentioned by Modi, with evidence from academic_search to justify decisions without delving into unrelated theory.",
      "section_type": "section"
    },
    {
      "node_id": "n5",
      "parent_id": "n1",
      "level": 1,
      "title": "Step-by-Step Implementation with Decision Points",
      "description": "This chapter provides a sequential guide for practitioners to implement shortage mitigation strategies, including decision points on resource allocation, using forum_search for practical insights and data_extraction to adapt India's approaches to local contexts.",
      "section_type": "chapter"
    },
    {
      "node_id": "n6",
      "parent_id": "n5",
      "level": 2,
      "title": "Core Steps for Supply Chain Adjustments",
      "description": "This section breaks down the implementation process, from assessing imports to domestic alternatives, with decision points informed by financial_search for cost analysis and web_search for current trade data related to India's LPG imports.",
      "section_type": "section"
    },
    {
      "node_id": "n7",
      "parent_id": "n5",
      "level": 2,
      "title": "Key Decision Points in Escalation",
      "description": "This section addresses choices like invoking lockdowns, using evidence from legal_search on India's policies and video_search for Modi's public addresses to guide practitioners on escalation based on shortage severity.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n1",
      "level": 1,
      "title": "Ensuring Effective Outcomes",
      "description": "This chapter covers handling uncertainties and validating strategies, focusing on practical performance metrics for practitioners monitoring LPG shortages, with dataset_search for impact data and standards_search for compliance checks.",
      "section_type": "chapter"
    },
    {
      "node_id": "n9",
      "parent_id": "n8",
      "level": 2,
      "title": "Managing Edge Cases and Failure Modes",
      "description": "This section identifies common pitfalls, such as prolonged wars exacerbating shortages, and strategies to mitigate them, drawing on historical data from news_archive to inform decisions on alternative energy sources in India's context.",
      "section_type": "section"
    },
    {
      "node_id": "n10",
      "parent_id": "n8",
      "level": 2,
      "title": "Validation and Performance Considerations",
      "description": "This section outlines methods to validate interventions and evaluate complexity, using performance metrics from financial_search and academic_search where it directly informs efficiency decisions for India's LPG management.",
      "section_type": "section"
    }
  ]
}
```

