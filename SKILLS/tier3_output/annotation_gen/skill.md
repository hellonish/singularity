# annotation_gen

**Tier**: output  
**Name**: `annotation_gen`  

## Description

The `annotation_gen` skill is a specialized, LLM-driven analytical process that transforms a curated list of academic sources into a formal annotated bibliography. It performs a deep, structured, and critical evaluation of each source individually. The core cognitive process involves: (1) parsing and interpreting the provided source metadata and content summaries, (2) conducting a multi-faceted critical analysis against a fixed schema, and (3) synthesizing this analysis into a concise, standalone annotation for each entry. The physical data transformation it applies is the conversion of an input list of source objects (each containing a `citation_id`, `formatted_citation`, and associated content data) into an OutputDocument—a structured list where each item is an enhanced object containing the original `citation_id` and `formatted_citation`, now paired with a newly generated `annotation` text. Each annotation is a coherent paragraph that methodically addresses the source's scholarly contribution, the authority of its authors/publication, and a set of predefined potential limitations. This skill does not conduct new research or retrieve sources; it performs a rigorous, interpretive analysis on the provided source materials.

## When to Use

Use this skill in the following specific scenarios:
*   **Upstream Dependencies**: This skill is a terminal or near-terminal output node. It REQUIRES upstream processing to provide a cleaned, deduplicated, and contextually relevant list of academic sources. The expected input format is a list of objects, where each object minimally contains a `citation_id` (a unique identifier), a `formatted_citation` (in a standard style like APA, MLA, or Chicago), and sufficient content data (e.g., abstracts, summaries, key findings from `summarize_source` or `extract_claims`) to perform a critical analysis. It is typically preceded by skills like `source_selection`, `summarize_source`, or `lit_review_organizer`.
*   **Primary Use Case**: When the final required output is a formal annotated bibliography for academic research, literature review sections, dissertation chapters, or research proposals where a source-by-source critical evaluation is explicitly needed.
*   **Secondary Use Case**: When you need to generate a evaluative summary of a set of sources to assess the overall strength, bias, and coverage of the collected literature before synthesizing arguments.
*   **Downstream Nodes**: The output of this skill is usually a final product. It may be passed directly to a `report_writer` or `document_formatter` for integration into a larger document, but it is rarely processed further analytically. It should NOT be fed back into synthesis or claim-extraction skills.

**Edge Cases - When NOT to Use This Skill:**
*   **For Simple Summaries**: If the task only requires a plain, non-critical summary of sources without evaluation of authority or limitations, use `summarize_source` instead.
*   **For Synthesized Arguments**: If the goal is to weave sources together into a cohesive narrative or argument about a topic, use `lit_review_writer` or `synthesis_writer`.
*   **Without Source Content**: Do not invoke this skill if only a raw list of citations (without abstracts/summaries) is available. It will hallucinate content.
*   **For Non-Scholarly Sources**: This skill's analytical framework is optimized for academic journals, books, and conference proceedings. It is less effective for analyzing news articles, blog posts, or social media without significant prompt adaptation.

## Execution Model

LLM-based

**Prompt file**: `prompts/annotation_gen.md`

## Output Contract

OutputDocument — list of {citation_id, formatted_citation, annotation}

## Constraints

*   **Strict Analytical Schema**: Each generated annotation MUST explicitly address, in a structured manner: 1) The source's core **contribution** to the field, 2) The **authority** of the authors, institution, or publication venue, and 3) Key **limitations** such as sample size, jurisdictional focus, recency/temporal relevance, funding sources, or methodological constraints. The LLM must not omit any of these required categories.
*   **No Hallucination of Source Content**: The annotation must be derived strictly from the provided source data (citation and content summaries). The LLM is forbidden from inventing details about the source's findings, methods, or conclusions that are not supported by the provided input. Phrases like "the paper discusses" or "the authors argue" must be grounded in the given text.
*   **Concise Output**: Each annotation must be a single, well-formed paragraph. Avoid bullet points or markdown formatting within the annotation field. The total length per annotation should be optimized for readability, typically between 80-150 words.
*   **Preservation of Input Data**: The skill must output the exact `citation_id` and `formatted_citation` string provided in the input for each source. These fields must not be altered, re-formatted, or truncated.
*   **Token Limit Awareness**: The input list of sources may be large. The Planner must consider the context window limits of the execution LLM. If the combined content of all sources to analyze exceeds practical token limits, the task must be broken into sequential batches using this same skill, or a pre-filtering step (`source_selection`) must be applied upstream.
*   **Scope Limitation**: This skill analyzes sources in isolation. It does not perform comparative analysis between sources or generate overarching themes. Its scope is strictly per-source critical annotation.