# contradiction_detect

**Tier**: analysis  
**Name**: `contradiction_detect`  

## Description

This skill performs a detailed, multi-faceted logical and semantic analysis to identify and characterize explicit and implicit contradictions between factual claims, methodological approaches, or interpretive statements across two or more distinct information sources. It operates as a critical quality control and reasoning layer within an information processing pipeline.

**Cognitive Process & Physical Action:**
1.  **Input Ingestion & Pairing:** The skill ingests a collection of claims, each annotated with its source identifier. It systematically generates all possible non-redundant pairs of claims from different sources for comparison.
2.  **Semantic Decomposition:** For each claim pair, the LLM decomposes the core propositions, identifying the subject, predicate, quantifiers (e.g., "all," "some," "none"), modalities (e.g., "possible," "necessary"), temporal contexts, and evaluative stances.
3.  **Logical Relationship Mapping:** It applies formal and informal logic rules to map the relationship between the decomposed propositions. This includes checking for direct logical negations (A vs. not-A), contrary relationships (both cannot be true), subcontrary relationships (both cannot be false), and contrariety under a shared quantifier.
4.  **Contextual & Pragmatic Analysis:** Beyond pure logic, the skill evaluates pragmatic implications, contextual frames, and disciplinary assumptions. It discerns if a difference in conclusion stems from a difference in underlying data, methodological choice (e.g., different statistical models), or fundamental interpretive lens.
5.  **Contradiction Typology & Severity Assessment:** Each identified contradiction is classified by `type` (`factual`, `methodological`, `interpretive`) and assigned a `severity` (e.g., high for direct factual negation on a central point, medium for methodological conflict affecting conclusions, low for minor interpretive differences on peripheral aspects).
6.  **Evidence Extraction & Justification:** For each flagged contradiction, the skill extracts the specific phrases or data points from the source texts that form the basis of the conflicting claims, ensuring the finding is grounded and auditable.

**Data Transformation:** The skill transforms an unstructured or semi-structured list of source-annotated claims into a structured, actionable report of inter-source conflicts. It adds metadata (`type`, `severity`) and relational context (`source_a`, `source_b`) to raw claim text, converting potential noise into a prioritized signal for downstream resolution.

## When to Use

**Specific Scenarios:**
*   **Pre-Synthesis Verification:** Immediately before a `synthesize` or `summarize` skill in a research or intelligence pipeline, to ensure the synthesis is aware of and can address fundamental disagreements in the source material.
*   **Source Credibility Assessment:** When evaluating the reliability of multiple sources on a topic, to identify points of dispute that may indicate bias, error, or evolving understanding.
*   **Hypothesis Generation in Investigative Work:** In investigative or diagnostic tasks, contradictions can be key clues. Use this skill to systematically surface all points of disagreement across witness statements, reports, or data logs.
*   **Literature Review or State-of-the-Art Analysis:** To map the scholarly or technical debate on a subject by categorizing the nature and severity of disagreements between key papers or experts.

**Upstream Dependencies & Expected Input Format:**
*   **Primary Upstream Skill:** `extract_claims` or a similar information extraction skill. This skill **requires** its input to be a list of discrete claims, where each claim is a concise, propositional statement.
*   **Required Input Metadata:** Each claim **must** be tagged with a unique and consistent `source` identifier (e.g., `source_id: "doc_1"`, `author: "Smith et al. 2023"`). The skill cannot function if all claims are from the same source or are untagged.
*   **Input Data Structure:** Expects data in a format that allows pairing, typically a list of dictionaries like `[{"claim": "The policy reduced emissions by 15%.", "source": "Report_A"}, {...}]`.

**Edge Cases - When NOT to Use:**
*   **Single-Source Analysis:** Do not use if all claims originate from a single document or speaker; it is designed for cross-source comparison.
*   **Vague or Non-Propositional Input:** Do not use on raw narrative text, long paragraphs, or questions. It requires pre-processed, extracted claims.
*   **As a Resolution Tool:** This skill is a detector, not an arbitrator. Do not invoke it expecting a resolution or a determination of which claim is correct.
*   **For Simple Fact-Checking Against a Ground Truth:** If you have a known, verified ground truth database, use a `fact_check` or `verify_against_knowledge_base` skill instead.

**Typical Downstream Nodes:**
*   `prioritize_contradictions`: To rank identified contradictions by severity or impact for focused attention.
*   `investigate_source`: To gather more context or metadata about the sources involved in a high-severity contradiction.
*   `seek_adjudicating_source`: To find additional, authoritative sources that might resolve the flagged contradiction.
*   `synthesize_with_caveats`: A synthesis skill explicitly designed to incorporate and note contradictions in its output.
*   `human_in_the_loop_alert`: To escalate high-severity factual contradictions for human review and decision-making.

## Execution Model

LLM-based

**Prompt file**: `prompts/contradiction_detect.md`

## Output Contract

AnalysisOutput — contradictions: [{claim, source_a, source_b, type, severity}]

## Constraints

*   **Scope Limitation - Detection Only:** This skill is strictly a detection and classification module. It **must NOT** attempt to resolve the contradiction, determine which source is correct, or generate new reconciled claims. Any such behavior is a hallucination outside its scope.
*   **Input Dependency:** It is wholly dependent on the quality and granularity of the upstream claim extraction. It cannot compensate for poorly extracted or overly broad claims.
*   **Claim-Pair Limitation:** It analyzes contradictions at the claim-pair level. It is not designed to detect higher-order contradictions involving three or more claims forming an inconsistent set, unless that inconsistency manifests in pairwise comparisons.
*   **Typology Adherence:** The `type` field must be constrained to the defined categories: `factual` (direct conflict on observable states or events), `methodological` (conflict in approach, technique, or data interpretation framework), or `interpretive` (conflict in conclusion, meaning, or significance derived from similar facts). The LLM must not invent new types.
*   **Severity Grounding:** The assignment of `severity` must be justified within the analysis based on the centrality of the claim to the source's main argument and the degree of logical opposition. Avoid arbitrary severity scores.
*   **Avoiding Trivial Negations:** The skill should be instructed to avoid flagging trivial linguistic negations or minor phrasing differences that do not represent a substantive contradiction in meaning. Focus on semantically significant conflicts.