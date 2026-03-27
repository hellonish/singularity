# bibliography_gen

**Tier**: output  
**Name**: `bibliography_gen`  

## Description

This skill is the final, authoritative node responsible for the physical compilation, formatting, and systematic presentation of all bibliographic references used within a generated report or document. It performs a critical data transformation from raw citation metadata stored in the system's CitationRegistry into a polished, structured bibliography section that adheres to a specific, formal citation style guide.

The cognitive process involves several distinct phases:
1.  **Registry Retrieval & Aggregation**: The skill first queries the central CitationRegistry, which is populated by upstream research and writing agents. It retrieves the complete, deduplicated set of all source objects that have been cited via in-text citations (e.g., `[1]`, `(Smith, 2023)`).
2.  **Style Mapping & Rule Application**: Based on the specified style (APA 7, Bluebook, IEEE, Vancouver), the skill applies a complex set of deterministic formatting rules. This includes:
    *   **Author/Contributor Formatting**: Reordering names (Last, First vs. First Last), handling et al. rules, and applying punctuation.
    *   **Title Formatting**: Applying title case, sentence case, or italicization/quote marks to article, book, and website titles.
    *   **Publication Data Structuring**: Correctly placing and punctuating journal names, volume/issue numbers, page ranges, publisher locations and names, DOIs, URLs, and retrieval dates.
    *   **Sorting Logic**: Alphabetizing entries by author surname (APA, Bluebook), by citation order (IEEE, Vancouver), or by other style-specific rules.
3.  **Data Validation & Gap Handling**: Each citation object is inspected for required fields (e.g., author, title, year). If critical data is missing, the skill does not guess or hallucinate information. Instead, it flags the entry by appending a standard disclaimer (e.g., `[incomplete citation — verify manually]`) to the formatted entry, ensuring transparency and mandating human verification.
4.  **Physical Assembly**: The skill assembles the validated and formatted entries into a final string output. This includes adding a section header (e.g., "References," "Bibliography," "Works Cited"), applying consistent hanging indents or numbered lists as per the style, and ensuring correct line spacing and punctuation throughout the entire list.

The output is a self-contained, ready-to-publish bibliography that provides the necessary information for a reader to locate each cited source.

## When to Use

*   **Specific Scenarios**:
    *   **Final Report Compilation**: As the concluding step after a `report_generator` skill has produced a full-length document containing in-text citations.
    *   **Executive Summary Support**: Following an `exec_summary` skill, if the summary itself cites sources that require a standalone reference list.
    *   **Standalone Reference List Generation**: When the primary task is to produce a formatted bibliography from a provided set of source metadata, even without a full report (e.g., "format these 20 papers in IEEE style").
*   **Upstream Dependencies & Input Format**:
    *   **Mandatory Dependency**: A populated **CitationRegistry**. This registry must be seeded by upstream skills like `research_agent`, `web_search`, or `report_generator` that explicitly log their used sources with complete metadata (author, title, publication, date, URL/DOI, etc.). The skill expects this registry to be available in the shared execution context.
    *   **Input Trigger**: The skill is triggered by the presence of a `citation_style` parameter (defaulting to "APA 7") and the completion of the main content-generating node.
*   **Edge Cases - When NOT to Use**:
    *   **No Citations Exist**: Do not invoke this skill if the CitationRegistry is empty or if the preceding document contains zero in-text citations. An empty bibliography is nonsensical.
    *   **For In-Text Citation Formatting**: This skill does not handle the insertion or formatting of citations within the body text (e.g., changing `(Smith et al.)` to `(Smith et al., 2023)`). That is the responsibility of the writing/report generator agent.
    *   **For Source Discovery or Evaluation**: This skill does not find new sources or assess source quality. It is a pure formatting and compilation tool.
    *   **Before Final Content is Frozen**: Do not run this skill iteratively during draft generation. It should be executed once, after all research and writing is complete and the citation list is final.
*   **Downstream Nodes**:
    *   Typically, this skill has **no downstream nodes**. Its output (`formatted_bibliography`) is a terminal product.
    *   Its output may be passed to a final `document_assembler` or `pdf_generator` skill that integrates the bibliography string into the complete final document file.

## Execution Model

LLM-based + CitationRegistry

**Prompt file**: `prompts/bibliography_gen.md`

## Output Contract

OutputDocument — formatted_bibliography string

## Constraints

*   **Style Scope Limitation**: The skill is strictly constrained to the following predefined citation styles: **APA 7 (default), Bluebook (legal), IEEE (technical), Vancouver (medical)**. The Planner must NOT instruct it to use other styles like MLA, Chicago, or Harvard. If an unsupported style is requested, default to APA 7.
*   **No Hallucination of Data**: Under NO circumstances may the skill invent, infer, or guess missing bibliographic fields (author names, publication dates, etc.). Its operation must be deterministic based on the provided CitationRegistry data.
*   **Incomplete Citation Protocol**: When any citation object is missing **author, title, or year** (or style-equivalent core fields), the skill MUST append the exact marker `[incomplete citation — verify manually]` to that specific entry. It must not skip the entry or fail entirely.
*   **Registry Dependency**: The skill is wholly dependent on the CitationRegistry. If the registry is missing, corrupted, or not passed in the execution context, the skill will fail. The Planner must ensure upstream agents have correctly logged their sources.
*   **Token Limit Awareness**: For documents with extremely large numbers of citations (e.g., >150), the final formatted bibliography string may be long. The Planner should ensure the output context window of the executing LLM can accommodate this.
*   **Single Responsibility**: The skill performs formatting and compilation only. It does not validate the authenticity of URLs/DOIs, check for paywalls, or assess the academic credibility of the sources. This is outside its scope.