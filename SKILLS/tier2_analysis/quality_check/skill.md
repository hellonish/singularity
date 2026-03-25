# quality_check

**Tier**: analysis  
**Name**: `quality_check`  

## Description

The `quality_check` skill is a rigorous, LLM-driven validation gate that performs a multi-axis evaluation of a node's output against a predefined set of acceptance criteria (axes). It functions as a critical quality control mechanism within the execution DAG, ensuring that intermediate or final outputs meet minimum standards before being passed to downstream nodes or considered complete. The skill does not modify the content it evaluates; instead, it applies a structured cognitive framework to assess it.

**Physical Process**: The skill takes the target node's output (the `content_to_evaluate`) and its defined `acceptance_axes` as primary inputs. It uses a specialized LLM prompt (`prompts/quality_check.md`) to conduct the evaluation. The LLM is instructed to analyze the content against each axis independently, scoring its performance on a scale (typically 0.0 to 1.0 or 0-100), determining if it passes a pre-configured threshold for that axis, and providing a concise, evidence-based reason for the score.

**Cognitive Process & Data Transformation**: The LLM parses the `acceptance_axes`, which are a list of quality dimensions (e.g., `factual_grounding`, `completeness`, `clarity`, `relevance`, `actionability`). For each axis, it:
1.  **Interprets the Axis**: Understands the semantic meaning of the quality dimension (e.g., "factual_grounding" means information is verifiable and not hallucinated).
2.  **Extracts Evidence**: Scans the `content_to_evaluate` for text segments that demonstrate adherence to or violation of the axis.
3.  **Scores & Judges**: Assigns a numerical score based on the evidence and makes a binary pass/fail judgment by comparing the score to a pre-defined threshold for that axis.
4.  **Synthesizes Report**: Aggregates the per-axis results into a final, structured `QualityReport` object. The `overall_pass` is a logical AND of all individual axis pass/fail results. If the overall check fails, the skill also generates a `remediation_suggestion` summarizing the primary deficiencies.

The input (content, axes) is thus transformed into a structured diagnostic report (`QualityReport`) that quantifies quality and pinpoints failures.

## When to Use

Use this skill as a **gatekeeping or validation node** immediately following any node where output quality is non-negotiable and must be verified before proceeding.

**Specific Scenarios**:
*   **After a Retrieval-Augmented Generation (RAG) Node**: To gate the output of a `query_contextualizer` or `answer_synthesizer`, checking for `factual_grounding` against retrieved contexts and `completeness` in answering the query.
*   **After an Analysis or Summarization Node**: To validate that a `summarize` or `analyze_sentiment` node's output is `coherent`, `concise`, and `faithful` to the source material.
*   **Before a Final Output Node**: As a final quality gate before a `response_formatter` or `report_generator` to ensure all acceptance criteria are met for the end-user.
*   **After a Code Generation Node**: To check for `correctness` (against a spec), `clarity` (of comments), and `security` (of patterns used).

**Upstream Dependencies & Input Format**:
This skill **requires** two specific upstream outputs:
1.  `content_to_evaluate`: (String) The raw text output from the preceding node that needs assessment.
2.  `acceptance_axes`: (List of Strings) The list of quality dimensions to evaluate against. These must be defined in the plan or by a prior node (e.g., a `spec_parser`). Example: `["factual_grounding", "completeness", "conciseness"]`.

**Edge Cases - When NOT to Use**:
*   **DO NOT** use it to evaluate purely subjective or creative content where objective axes cannot be defined (e.g., "Is this poem beautiful?").
*   **DO NOT** use it as the first node in a DAG; it must have a predecessor that generates the `content_to_evaluate`.
*   **DO NOT** use it to evaluate the quality of its own output (no recursive checks).
*   **DO NOT** use it if the acceptance axes are undefined, ambiguous, or contradictory.

**Typical Downstream Nodes**:
*   **On Success (`overall_pass=True`)**: The validated content proceeds to the next logical node in the workflow (e.g., `response_formatter`, `next_analysis_step`).
*   **On Failure (`overall_pass=False`)**: The orchestrator automatically generates a `GapItem`. The DAG typically then routes to a remediation skill (e.g., `rewrite`, `expand_content`, `fact_check`) tasked with addressing the specific deficiencies noted in the `QualityReport`.

## Execution Model

LLM-based

**Prompt file**: `prompts/quality_check.md`

## Output Contract

QualityReport — {axes_evaluated, results: {axis: {passed, score, reason, threshold}}, overall_pass, remediation_suggestion}

## Constraints

*   **Threshold Enforcement**: The default threshold for the `factual_grounding` axis is **0.80**. Scores below this constitute a failure. Thresholds for other axes (e.g., `completeness`, `clarity`) are domain-specific and must be explicitly defined in the task context or plan. The LLM must apply these thresholds strictly, not infer them.
*   **No Hallucination in Evaluation**: The LLM's `reason` for each axis must be directly supported by evidence from the `content_to_evaluate`. It must not invent failures or virtues not present in the text.
*   **Strict Scope Limitation**: The evaluation must be confined **only** to the provided `content_to_evaluate` and the defined `acceptance_axes`. It must not introduce new axes, evaluate based on external knowledge not contained in the content, or assess the quality of the upstream task itself, only the output's adherence to the axes.
*   **Automatic Gap Generation**: If `overall_pass=False`, the orchestrator will automatically create a `GapItem`. The `remediation_suggestion` in the report must be clear and actionable to facilitate this.
*   **Deterministic Judgment**: The pass/fail judgment is a deterministic function of (score >= threshold). The LLM must not allow subjective leniency.