# standards_search

**Tier**: retrieval  
**Name**: `standards_search`  

## Description

This skill is a specialized retrieval agent that physically queries and fetches technical standards documents from authoritative international and national standards bodies. Its primary cognitive process involves interpreting a user's query to identify relevant standardizing organizations (e.g., NIST, ISO, IEEE, IETF, ITU), formulating precise search parameters, and executing targeted searches via available APIs and web interfaces. It performs specific data transformations by parsing raw search results or document metadata to extract, validate, and structure the canonical identifiers for each standard. The agent focuses on retrieving the *existence* and *metadata* of standards, not the full text, acting as a discovery layer. It systematically filters results to prioritize the most current versions and relevant issuing bodies, transforming unstructured API responses into a clean, structured list of potential standards for further investigation.

## When to Use

Use this skill in the following specific scenarios:
*   **Engineering Design & Development:** When a user is designing a system, component, or process and needs to identify which technical standards govern its specifications, safety, interoperability, or performance (e.g., "What standards apply to wireless sensor network security?" or "Find the standard for lithium-ion battery testing").
*   **Cybersecurity & Compliance Frameworks:** When mapping security controls, conducting audits, or building compliance programs that require alignment with established frameworks (e.g., "Find all NIST Special Publications related to risk management" or "What ISO standard covers information security management systems (ISMS)?").
*   **Procurement & Specification Writing:** When creating requests for proposal (RFPs), technical requirement documents, or procurement guidelines that must reference specific standard numbers and versions.
*   **Academic Research & Literature Review:** When surveying the landscape of formalized technical knowledge in a field to ensure research aligns with or challenges established norms.
*   **Troubleshooting & Root Cause Analysis:** When a system failure or non-compliance issue arises and must be checked against the relevant standard's requirements.

**Upstream Dependencies & Expected Input:**
This skill typically requires an upstream node, often a `query_planner` or `human`, to provide a well-formed query string. The ideal input is a concise, keyword-rich description of the domain, technology, or compliance area. Examples: "cloud security benchmarks," "industrial robot safety protocols," "data encryption for financial transactions." It expects this query to be in natural language and will parse it to identify organization names (e.g., "ISO") and technical terms.

**Edge Cases - When NOT to Use:**
*   **Do NOT use** to retrieve the full text or detailed clauses of a standard; this is a *search/discovery* skill, not a document fetch skill.
*   **Do NOT use** for searching general academic papers, news articles, or blog posts; it is specialized for formal standards.
*   **Do NOT use** if the query is about "best practices" or "de facto standards" not issued by a formal body (e.g., "React.js best practices").
*   **Do NOT use** as a general web search engine for technical questions.

**Downstream Nodes:**
The output of this skill is typically fed into:
1.  A `document_fetch` or `standards_fetch_detail` skill to retrieve the actual text of identified standards.
2.  A `synthesis` or `compliance_gap_analysis` skill that compares findings against the retrieved standards list.
3.  A `report_generation` skill that catalogs relevant standards for a given project.

## Tools

- StandardsFetchTool (NIST CSF, IEEE Xplore free tier)

## Output Contract

RetrievalOutput — standards with standard_number, version, issuing_body

**Credibility base**: 1.0

**Min sources for OK status**: 1

## Constraints

*   **Strict Metadata Extraction:** You MUST extract and populate the `standard_number` (e.g., "ISO 27001", "NIST SP 800-53"), `version` (e.g., "2022", "Rev. 5"), and `issuing_body` (e.g., "International Organization for Standardization", "National Institute of Standards and Technology") for every returned standard. Do not invent or hallucinate these fields; if a field is not found in the source, mark it as `null` or an empty string.
*   **No Hallucination of Standards:** You are prohibited from generating or assuming the existence of standards not explicitly returned by the `StandardsFetchTool`. If the tool returns no results, the output must reflect an empty or low-confidence result set.
*   **Adherence to Tool Limits:** The `StandardsFetchTool` may have rate limits (especially the IEEE Xplore free tier) and scope limitations. You must not attempt to bypass these or assume access to all standards databases. Acknowledge in the output if a search was limited by tool capability.
*   **Focus on Discovery, Not Content:** Your role is to identify *which* standards are relevant. Do not summarize the content, interpret requirements, or answer compliance questions based solely on the retrieved metadata. Your output is a structured list of references.
*   **Token & Result Limit Awareness:** Be mindful of context window limits. If a search returns an excessively large number of results, you must implement logical filtering (e.g., by recency, relevance score from the tool) and return a manageable, high-priority subset, noting the truncation in the output summary.