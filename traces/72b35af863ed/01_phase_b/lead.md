# Lead Agent — Final Report Structure

## System Prompt

# REPORT LEAD

You are the Report Lead. Three Manager agents have each proposed a hierarchical
report structure. Your job is to select the best one, or intelligently merge elements
from multiple proposals, to produce the single best final structure.

## Your Role

You think like an editor-in-chief. You receive three proposals and must produce one
definitive tree. You are the final authority on structure — your output is not
reviewed again.

## Selection / Merge Rules

1. **Count constraint is non-negotiable.** The final tree must have a node count
   within the target range given in the input. Count before emitting and trim or
   fill to stay in range.
2. The three proposals were generated from different structural perspectives
   (concept-first / problem-first / practitioner-workflow). Prefer a synthesis
   that combines the best elements of multiple perspectives over selecting one
   verbatim — the goal is a structure no single manager could produce alone.
3. You may take the skeleton of one proposal and replace individual chapters or
   sections with stronger alternatives from another.
4. You may reorder chapters or sections within a level.
5. You may write a new title or description that better captures a merged idea,
   as long as the content is grounded in what the proposals collectively cover.
6. Add a `reasoning` field to the root node explaining which perspectives you
   drew from for which parts, and why.

## Quality Criteria (what makes the best structure)

- **Completeness**: all key aspects of the query are covered
- **No overlap**: sibling sections don't repeat the same evidence
- **Logical flow**: a reader can follow the argument from start to end
- **Appropriate depth**: subsections exist where genuine depth is needed, not as padding
- **Audience fit**: complexity and framing suit the stated audience

## Output — respond ONLY with this JSON, no prose

```json
{
  "final_tree": {
    "proposal_id": "lead_final",
    "total_nodes": 0,
    "rationale": "Overall organising principle of the final structure",
    "reasoning": "Which proposals were used for which parts, and why",
    "sources_used": ["manager_1", "manager_2", "manager_3"],
    "tree": [
      {
        "node_id": "n1",
        "parent_id": null,
        "level": 0,
        "title": "...",
        "description": "...",
        "section_type": "root"
      }
    ]
  }
}
```

CRITICAL: Count every object in the `tree` array. `total_nodes` must match that count
and must be within the target range specified in the input. Fix it if not.


## User Message (includes Manager Proposals)

query: LPG Shortage in India due to US-Iran War, and multiple opinions, Prime Minister of India - Narendra Modi mentioned a lockdown might occur, I want a deep study report for this. What is India's take on it
audience: practitioner
target_section_count_range: 6–10 (stay within this range)

## Manager Proposals

[
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
  },
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
  },
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
]

## Raw LLM Response

```
{
  "final_tree": {
    "proposal_id": "lead_final",
    "total_nodes": 8,
    "rationale": "This structure integrates a problem-first approach with practitioner-oriented workflow elements, ensuring a logical progression from understanding the LPG shortage issue in India to actionable strategies, tailored for a practitioner audience. It balances real-world context, essential theory, and practical implementation to provide a comprehensive yet focused report.",
    "reasoning": "The skeleton is adapted from Manager 2's problem-first approach, particularly the use of a motivating case study to ground the report in real-world impacts, ensuring audience engagement and relevance. Manager 3's practitioner workflow perspective is incorporated in the implementation and decision-making sections to provide actionable steps and address the audience's need for practical guidance. Manager 1's conceptual depth is selectively used in the background section to provide necessary geopolitical and economic context without overwhelming with excessive theory. This synthesis ensures completeness, logical flow, and audience fit while avoiding overlap and maintaining appropriate depth. Sections were trimmed and merged to fit the target node count range of 6-10.",
    "sources_used": ["manager_1", "manager_2", "manager_3"],
    "tree": [
      {
        "node_id": "n1",
        "parent_id": null,
        "level": 0,
        "title": "Comprehensive Study of LPG Shortage in India Amid US-Iran War",
        "description": "This report examines the LPG shortage in India triggered by the US-Iran War, blending real-world case studies, essential context, and practitioner-focused strategies to address the crisis, with a focus on India's perspective and policy responses.",
        "section_type": "root"
      },
      {
        "node_id": "n2",
        "parent_id": "n1",
        "level": 1,
        "title": "Real-World Impact of LPG Shortage",
        "description": "Presents a specific case of LPG supply disruptions in India to highlight immediate effects on households and businesses, immersing practitioners in the problem before deeper analysis.",
        "section_type": "chapter"
      },
      {
        "node_id": "n3",
        "parent_id": "n2",
        "level": 2,
        "title": "Case Study: Disruptions in Daily Life",
        "description": "Details how the shortage affects everyday activities in an Indian city, using news archives and forum insights to showcase practical challenges faced by communities.",
        "section_type": "section"
      },
      {
        "node_id": "n4",
        "parent_id": "n1",
        "level": 1,
        "title": "Geopolitical and Economic Context",
        "description": "Provides essential background on the US-Iran War's impact on global energy supplies and India's specific vulnerabilities, ensuring practitioners understand the root causes of the shortage.",
        "section_type": "chapter"
      },
      {
        "node_id": "n5",
        "parent_id": "n4",
        "level": 2,
        "title": "US-Iran War's Effect on LPG Supply Chains",
        "description": "Explains how the conflict disrupts global LPG supplies and directly affects India, using news and dataset evidence to clarify the geopolitical trigger.",
        "section_type": "section"
      },
      {
        "node_id": "n6",
        "parent_id": "n1",
        "level": 1,
        "title": "India's Response and Policy Framework",
        "description": "Analyzes India's official stance, including Narendra Modi's lockdown statements, and policy shifts to address the shortage, providing a national perspective for practitioners.",
        "section_type": "chapter"
      },
      {
        "node_id": "n7",
        "parent_id": "n6",
        "level": 2,
        "title": "Strategic Interventions and Decision Points",
        "description": "Outlines key policy responses and decision points, such as potential lockdowns, with evidence from government sources and public addresses to guide practitioner actions.",
        "section_type": "section"
      },
      {
        "node_id": "n8",
        "parent_id": "n1",
        "level": 1,
        "title": "Practitioner Guide to Mitigation Strategies",
        "description": "Offers a step-by-step workflow for managing LPG shortages, focusing on actionable strategies and performance evaluation to ensure effective outcomes in India's context.",
        "section_type": "chapter"
      }
    ]
  }
}
```

## Final Tree (JSON)

```json
{
  "proposal_id": "lead_final",
  "rationale": "This structure integrates a problem-first approach with practitioner-oriented workflow elements, ensuring a logical progression from understanding the LPG shortage issue in India to actionable strategies, tailored for a practitioner audience. It balances real-world context, essential theory, and practical implementation to provide a comprehensive yet focused report.",
  "total_nodes": 8,
  "tree": [
    {
      "node_id": "n1",
      "parent_id": null,
      "level": 0,
      "title": "Comprehensive Study of LPG Shortage in India Amid US-Iran War",
      "description": "This report examines the LPG shortage in India triggered by the US-Iran War, blending real-world case studies, essential context, and practitioner-focused strategies to address the crisis, with a focus on India's perspective and policy responses.",
      "section_type": "root"
    },
    {
      "node_id": "n2",
      "parent_id": "n1",
      "level": 1,
      "title": "Real-World Impact of LPG Shortage",
      "description": "Presents a specific case of LPG supply disruptions in India to highlight immediate effects on households and businesses, immersing practitioners in the problem before deeper analysis.",
      "section_type": "chapter"
    },
    {
      "node_id": "n3",
      "parent_id": "n2",
      "level": 2,
      "title": "Case Study: Disruptions in Daily Life",
      "description": "Details how the shortage affects everyday activities in an Indian city, using news archives and forum insights to showcase practical challenges faced by communities.",
      "section_type": "section"
    },
    {
      "node_id": "n4",
      "parent_id": "n1",
      "level": 1,
      "title": "Geopolitical and Economic Context",
      "description": "Provides essential background on the US-Iran War's impact on global energy supplies and India's specific vulnerabilities, ensuring practitioners understand the root causes of the shortage.",
      "section_type": "chapter"
    },
    {
      "node_id": "n5",
      "parent_id": "n4",
      "level": 2,
      "title": "US-Iran War's Effect on LPG Supply Chains",
      "description": "Explains how the conflict disrupts global LPG supplies and directly affects India, using news and dataset evidence to clarify the geopolitical trigger.",
      "section_type": "section"
    },
    {
      "node_id": "n6",
      "parent_id": "n1",
      "level": 1,
      "title": "India's Response and Policy Framework",
      "description": "Analyzes India's official stance, including Narendra Modi's lockdown statements, and policy shifts to address the shortage, providing a national perspective for practitioners.",
      "section_type": "chapter"
    },
    {
      "node_id": "n7",
      "parent_id": "n6",
      "level": 2,
      "title": "Strategic Interventions and Decision Points",
      "description": "Outlines key policy responses and decision points, such as potential lockdowns, with evidence from government sources and public addresses to guide practitioner actions.",
      "section_type": "section"
    },
    {
      "node_id": "n8",
      "parent_id": "n1",
      "level": 1,
      "title": "Practitioner Guide to Mitigation Strategies",
      "description": "Offers a step-by-step workflow for managing LPG shortages, focusing on actionable strategies and performance evaluation to ensure effective outcomes in India's context.",
      "section_type": "chapter"
    }
  ]
}
```

