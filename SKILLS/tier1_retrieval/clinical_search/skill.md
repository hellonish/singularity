# clinical_search

**Tier**: retrieval  
**Name**: `clinical_search`  

## Description

This skill is a specialized, high-precision retrieval agent designed to execute simultaneous, targeted searches across two authoritative biomedical databases: PubMed (via the PubmedTool) and ClinicalTrials.gov (via the ClinicalTrialsTool). Its primary function is to gather, filter, and synthesize primary clinical evidence and trial data in response to a specific biomedical or clinical query. The cognitive process involves parsing the user's query to identify core clinical entities (e.g., drug names, conditions, biomarkers, interventions, outcomes), formulating optimized Boolean search strings tailored to each database's syntax, and executing parallel searches. It then performs a critical appraisal of the initial results, prioritizing sources based on evidence hierarchy (e.g., randomized controlled trials, systematic reviews, meta-analyses over case reports) and relevance to the query's clinical context. The agent applies specific data transformations by extracting, normalizing, and structuring key metadata from each source, including trial phase, unique identifiers (PMID or NCT Number), primary and secondary outcomes, intervention details, and study design. It synthesizes this into a coherent, evidence-graded summary, explicitly tagging the `clinical_significance` (e.g., "significant benefit," "no difference," "serious adverse events reported") where discernible from abstracts and registry entries. The output is a consolidated, source-attributed evidence base ready for downstream analysis or reporting.

## When to Use

- **Specific Scenarios**:
    1.  Answering questions about the efficacy, safety, or mechanism of a drug, biologic, or medical device for a specific condition.
    2.  Investigating the current state of clinical research (phases, status, recruitment) for a given intervention.
    3.  Supporting evidence-based medicine queries, such as "first-line treatment for condition X" or "standard of care for patient profile Y."
    4.  Conducting due diligence on a pharmaceutical asset by gathering published trial results and ongoing study registrations.
    5.  Preparing a literature overview for a clinical protocol, grant proposal, or regulatory document.
    6.  Comparing clinical outcomes between two or more therapeutic approaches.

- **Upstream Dependencies & Expected Input**:
    - This skill is typically a primary retrieval node. It expects an upstream input in the form of a **well-defined, clinically-focused natural language query**. The query should specify: the **Population/Patient group**, **Intervention**, **Comparator** (if applicable), and **Outcome** (PICO elements are ideal but not strictly required). Vague questions will yield suboptimal results. The input may come directly from a user or from a prior planning/query-refinement agent.

- **Edge Cases - When NOT to Use**:
    1.  **Non-Clinical Questions**: Do not use for basic biological mechanism questions (use `literature_search`), chemical synthesis, computational methods, or general health advice.
    2.  **Diagnostic or Image Interpretation**: Do not use for analyzing medical images or making diagnostic predictions.
    3.  **Patient-Specific Treatment Decisions**: This skill provides aggregated evidence, not personalized medical advice. It should not be the final node in a chain advising a specific patient.
    4.  **Extremely Novel or Pre-Clinical Topics**: If the query is about a target or molecule with no human data, results will be empty.
    5.  **Legal, Financial, or Commercial Queries**: Do not use to search for drug pricing, market analyses, or patent information.

- **Downstream Nodes That Usually Follow**:
    1.  **`evidence_summarizer`** or **`report_generator`**: To synthesize the retrieved evidence into a narrative summary or structured report.
    2.  **`clinical_risk_analyzer`**: To assess safety signals or risk-benefit profiles from the gathered data.
    3.  **`guideline_checker`**: To compare retrieved evidence against established clinical practice guidelines.
    4.  **`data_extractor`**: For further structured data mining from the full texts of retrieved PubMed articles (if accessible).

## Tools

- PubmedTool
- ClinicalTrialsTool

## Output Contract

RetrievalOutput — sources with trial phase, PMID/NCT, outcomes

**Credibility base**: 0.92 peer-reviewed; 1.0 clinical trial registry

**Min sources for OK status**: 2

## Constraints

1.  **Evidence Hierarchy Mandate**: To achieve an "OK" status output, **at least one retrieved source must be a clinical trial (any phase) or a systematic review/meta-analysis**. Case reports, editorials, or preclinical studies alone are insufficient. The Planner must ensure the query is scoped to likely yield this type of evidence.
2.  **Clinical Significance Extraction**: You **MUST** explicitly extract and report the `clinical_significance` metadata from each relevant source. This is not optional. Infer this from reported p-values, hazard ratios, confidence intervals, and author conclusions in abstracts. For trials, note primary endpoint success/failure.
3.  **Avoid Hallucination of Data**: You are strictly prohibited from inferring results not present in the abstract or registry entry. If outcomes are not reported, state "Outcomes not reported in abstract." Do not confound different trials or invent composite endpoints.
4.  **Token & Source Limit Awareness**: Be mindful of context windows. Prioritize the most recent and most relevant (by study size, phase, and design) sources. Do not attempt to retrieve and process an excessively large number of records (typically, aim for 3-5 highly relevant results per database).
5.  **Scope Limitation**: Your search is limited to PubMed and ClinicalTrials.gov. You cannot access full-text articles behind paywalls, other databases (e.g., Embase, Cochrane Central), conference proceedings, or regulatory documents (e.g., FDA EMA reports). Acknowledge this limitation if the query demands such sources.
6.  **Temporal Relevance**: For treatment-related queries, prioritize studies from the last 5-10 years unless historical context is explicitly requested. For ClinicalTrials.gov, clearly distinguish between completed, ongoing, and terminated studies.