# Retriever — Skill Selection Plan

## System Prompt

You are a retrieval planner. Return ONLY valid JSON with no prose. The JSON must have a single key 'skill_queries' mapping skill names to lists of query strings.

## User Prompt

mode: retrieval_plan
query: LPG Shortage in India due to US-Iran War, and multiple opinions, Prime Minister of India - Narendra Modi mentioned a lockdown might occur, I want a deep study report for this. What is India's take on it
report_sections (8 planned):
  - [n1] Comprehensive Study of LPG Shortage in India Amid US-Iran War: This report examines the LPG shortage in India triggered by the US-Iran War, ble
  - [n2] Real-World Impact of LPG Shortage: Presents a specific case of LPG supply disruptions in India to highlight immedia
  - [n3] Case Study: Disruptions in Daily Life: Details how the shortage affects everyday activities in an Indian city, using ne
  - [n4] Geopolitical and Economic Context: Provides essential background on the US-Iran War's impact on global energy suppl
  - [n5] US-Iran War's Effect on LPG Supply Chains: Explains how the conflict disrupts global LPG supplies and directly affects Indi
  - [n6] India's Response and Policy Framework: Analyzes India's official stance, including Narendra Modi's lockdown statements,
  - [n7] Strategic Interventions and Decision Points: Outlines key policy responses and decision points, such as potential lockdowns, 
  - [n8] Practitioner Guide to Mitigation Strategies: Offers a step-by-step workflow for managing LPG shortages, focusing on actionabl

Generate queries that will fetch evidence directly needed by these sections. Prioritise sections that require factual data, statistics, or source material.

available_skills: web_search, academic_search, clinical_search, legal_search, financial_search, news_archive, gov_search, code_search, patent_search, standards_search, forum_search, video_search, dataset_search, book_search, social_search, pdf_deep_extract, multimedia_search, data_extraction
select_n_skills: 1
queries_per_skill: 3

Return JSON: {"skill_queries": {"skill_name": ["query1", ...]}}
Select the 1 most relevant skills for this query.
Generate exactly 3 targeted sub-queries per skill, each serving a specific section from the list above.

## Raw LLM Response

```
{
  "skill_queries": {
    "news_archive": [
      "Recent news articles on Narendra Modi's statements regarding potential lockdown due to LPG shortage in India amid US-Iran War (for section n6)",
      "Reports on how the US-Iran War has disrupted global LPG supply chains and affected India (for section n5)",
      "Specific cases of LPG supply disruptions and their real-world impact in India (for section n2)"
    ]
  }
}
```

## Parsed Skill Queries (JSON)

```json
{
  "news_archive": [
    "Recent news articles on Narendra Modi's statements regarding potential lockdown due to LPG shortage in India amid US-Iran War (for section n6)",
    "Reports on how the US-Iran War has disrupted global LPG supply chains and affected India (for section n5)",
    "Specific cases of LPG supply disruptions and their real-world impact in India (for section n2)"
  ]
}
```

