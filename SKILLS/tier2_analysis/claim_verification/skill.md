# claim_verification

**Tier**: analysis
**Name**: `claim_verification`

## Description

This skill performs a rigorous, point-by-point factual audit of a synthesized document's key assertions. It is a critical quality control and validation step that operates by deconstructing the synthesis output into its constituent factual claims, tracing each claim back to its cited source material, and performing a detailed comparison to establish veracity. The physical process involves parsing the synthesis text to identify discrete propositions that are presented as factual statements, each typically accompanied by one or more citation identifiers (e.g., `[1]`, `[source_a]`). For each identified claim, the skill locates the corresponding source content using the provided citation mapping. It then executes a deep cognitive analysis, comparing the semantic content of the claim against the explicit information, context, and nuance present in the source. This is not a simple keyword match; it involves evaluating if the claim is directly supported, indirectly inferred, partially accurate, exaggerated, contradicted, or unsupported by the source text. The skill applies specific data transformations: it ingests a synthesis object and a sources object, extracts claims, maps them to source snippets, runs a verification LLM process, and outputs a structured verification report that annotates each claim with a detailed verdict and evidentiary reasoning.

## When to Use

- **Primary Scenario**: Immediately after any `synthesis` or `report_generation` skill in the execution DAG, when the integrity and factual fidelity of the generated content is paramount. This is essential for analytical reports, research summaries, or any output where credibility is critical.
- **Upstream Dependencies**: This skill **MUST** have two specific upstream data products:
    1.  **Synthesis Output**: The tier 2 `analysis_output` object containing the `synthesis` string with embedded citations (e.g., `[id]`). This is the text to be audited.
    2.  **Source Documents**: The complete `source_documents` object (or a relevant subset) that maps citation IDs to the actual source text content. The skill cannot operate without access to the full text of the cited sources.
- **Typical Downstream Nodes**: The verification output is typically consumed by:
    - A `report_refinement` or `editing` skill, which uses the verdicts to correct inaccuracies, qualify statements, or add disclaimers to the final report.
    - A `quality_assurance` orchestrator node that aggregates verification results to approve or reject the entire analysis pipeline output.
    - Direct inclusion in a final output to provide transparency, showing which claims are verified.
- **Edge Cases - When NOT to Use**:
    - **No Citations**: Do not use if the synthesis output contains no citations or factual claims (e.g., purely opinion or summary of methodology).
    - **Unavailable Sources**: Do not use if the full text of the cited sources is not accessible in the context. The skill will fail or hallucinate.
    - **Before Synthesis**: Do not use on raw source materials or extracted facts; it is designed to audit the *synthesized* narrative.
    - **For Simple Fact Extraction**: Do not use as a fact extraction tool from sources; use `information_extraction` for that purpose.

## Execution Model

LLM-based

**Prompt file**: `prompts/claim_verification.md`

## Output Contract

AnalysisOutput — verifications: [{claim, verified, supporting, contradicting, verdict}]

## Constraints

- **Source Content Mandate**: The skill **MUST** retrieve and evaluate the *actual textual content* from the source document corresponding to each `citation_id`. It is strictly forbidden to make a verification judgment based solely on the presence of a citation ID or a presumed topic match. The LLM must be explicitly prompted with the source text snippet.
- **Hallucination Prohibition**: The verification reasoning must be grounded exclusively in the provided synthesis claim and the provided source text. The LLM must not introduce external knowledge, make assumptions about unstated source content, or infer veracity from general world knowledge.
- **Claim Isolation**: Each verification must address a single, discrete claim from the synthesis. The skill must avoid bundling multiple ideas into one verification entry unless they are presented as a single, compound claim in the synthesis.
- **Scope Limitation**: The skill's scope is verification *against provided sources*. It does not:
    - Evaluate the logical soundness of arguments.
    - Judge the quality or reliability of the sources themselves.
    - Verify claims for which no source is cited (these should be flagged as "unsourced" or "unverifiable").
    - Perform cross-source reconciliation or resolve conflicts between sources (unless a single claim cites multiple conflicting sources).
- **Structured Output Adherence**: The output must strictly conform to the `AnalysisOutput` schema with the `verifications` array. Each object in the array must contain the exact fields: `claim` (string), `verified` (boolean), `supporting` (string array), `contradicting` (string array), and `verdict` (string explanation).