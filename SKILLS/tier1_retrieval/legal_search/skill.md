# legal_search

**Tier**: retrieval  
**Name**: `legal_search`  

## Description

The `legal_search` skill is a specialized retrieval agent that performs authoritative, jurisdiction-aware searches for primary legal sources, specifically case law and judicial opinions, from the CourtListener database. It physically executes a structured query to the CourtListener API via its dedicated tool, transforming a user's legal question or research topic into a targeted search for relevant precedents. The cognitive process involves: 1) Parsing the user's query to identify core legal issues, parties, cited statutes, or specific jurisdictions; 2) Constructing an optimized search query string that balances breadth (to capture relevant concepts) with precision (to avoid irrelevant results); 3) Executing the search and retrieving a raw result set from CourtListener; 4) Applying a mandatory jurisdiction filter if specified in the acceptance criteria; 5) Structuring and ranking the filtered results by relevance, typically considering factors like citation count, recency, and court level; and 6) Formatting the final output into a standardized `RetrievalOutput` object. The key data transformation is from an unstructured legal research need into a curated, citable list of case law entries, each with its metadata standardized.

## When to Use

Use this skill in the following specific scenarios:
- **Core Legal Research**: When the user's query explicitly asks for case law, legal precedents, court rulings, judicial opinions, or "how courts have ruled" on a specific issue (e.g., "find cases about non-compete agreements in California," "what is the precedent for fair use in AI training data?").
- **Regulatory & Compliance Analysis**: When analyzing the judicial interpretation of a statute, regulation, or legal doctrine. This is a prerequisite before offering compliance advice.
- **Policy Domain Exploration**: When researching the legal landscape or judicial trends surrounding a policy issue (e.g., "search for Supreme Court cases on affirmative action").
- **Supporting Legal Argumentation**: When building or validating a legal argument and needing authoritative citations to back a claim of what the law *is*.

**Upstream Dependencies & Expected Input**:
- This skill is typically a primary retrieval node in a DAG. It expects an upstream node (often a `query_understanding` or `planning` node) to provide a well-formulated **search query string**. This string should encapsulate the key legal terms, parties, statutes, or concepts. The skill itself does not extensively rephrase or expand queries; it uses the provided string directly.
- The Planner **must** provide the `acceptance_axes` parameter. Crucially, if jurisdiction is relevant, `jurisdiction_relevance` **must** be included in this axes dict, with the correct jurisdiction value (e.g., `"California"`, `"U.S. Federal"`, `"Supreme Court"`).

**Edge Cases - When NOT to Use**:
- **DO NOT USE** for searching statutory law, codes, or regulations (e.g., "find the text of 17 U.S.C. § 107"). This tool searches for *case law*.
- **DO NOT USE** for general factual or non-legal web searches. It is confined to the CourtListener database.
- **DO NOT USE** if the user is asking for *legal advice* or conclusions. This skill only retrieves sources; it does not synthesize or apply law to facts.
- **AVOID USING** for very recent events (last few days) where case law would not yet be published and indexed.

**Downstream Nodes**:
- The output is designed for nodes that synthesize, summarize, or apply retrieved law. Common downstream skills include:
    - `summarize`: To create briefs of the key holdings from retrieved cases.
    - `synthesize`: To integrate multiple case holdings into a coherent legal principle.
    - `answer_formulation`: To use the retrieved cases as citations in a final answer to a legal question.

## Tools

- CourtListenerTool

## Output Contract

RetrievalOutput — cases with citation, court, date_filed, jurisdiction

**Credibility base**: 0.95

**Min sources for OK status**: 1

## Constraints

- **HARD RULE - Jurisdiction Filtering**: If the key `'jurisdiction_relevance'` is present in the `acceptance_axes` dictionary provided by the Planner, you **MUST** filter the CourtListener search results to return **only** cases from that specified jurisdiction. Do not perform a broader search and then filter in description; the filter must be applied to the query execution itself. Ignoring this rule will cause the skill to fail its acceptance criteria.
- **Zero-Source Failure Condition**: If, after applying any required jurisdiction filter, the search returns **0 sources**, the skill's status must be set to **FAILED**. You must **NOT** attempt to compensate for this failure by falling back to a general web search or other non-authoritative sources to find "legal conclusions." Legal retrieval requires authoritative primary sources; absence of results is a significant finding that must be reported as a failure, not masked with inferior data.
- **Token & Scope Limit**: The skill should retrieve a manageable number of highly relevant cases (typically 3-7). Do not set query parameters to return an excessively large result set (e.g., 100+ cases), as this wastes tokens and processing time for downstream nodes. Focus on precision and the most cited/recent rulings.
- **Avoid Hallucination of Content**: This skill only retrieves and returns metadata (citation, court, date, jurisdiction) and snippets/previews provided by CourtListener. **DO NOT** generate or hallucinate details about the case holding, facts, or reasoning that are not present in the retrieved source material. The output is purely for retrieval.
- **No Legal Analysis**: Under no circumstances should this skill attempt to interpret, compare, or analyze the retrieved cases. Its function ends at source retrieval and basic relevance ranking.