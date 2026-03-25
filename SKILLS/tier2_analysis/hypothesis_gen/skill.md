# hypothesis_gen

**Tier**: analysis  
**Name**: `hypothesis_gen`  

## Description

This skill performs a structured, evidence-driven reasoning process to formulate novel, testable scientific hypotheses. It is a core analytical function that transforms identified knowledge gaps into actionable research propositions. The skill operates by first ingesting and synthesizing all available contextual evidence (e.g., from `gap_analysis`, `lit_review`, or `data_analysis`). It then identifies the most critical and promising areas of uncertainty within that evidence base. For each area, it cognitively models potential underlying mechanisms, causal relationships, or explanatory frameworks that could account for the observed data or fill the identified gap. This modeling is constrained by the existing evidence to ensure plausibility. Finally, it articulates these models as clear, falsifiable hypothesis statements, evaluates their inherent testability, and proposes concrete, feasible methods to test them. The output is not a list of guesses but a prioritized set of reasoned, evidence-anchored research directions designed to systematically reduce uncertainty.

## When to Use

Use this skill in the following specific scenarios:
*   **After `gap_analysis` or `lit_review`:** When upstream skills have explicitly cataloged evidence and pinpointed specific contradictions, missing data, or unanswered questions. The `hypothesis_gen` skill directly consumes these "evidence gap" lists as its primary input.
*   **Research Planning & Study Design:** When the goal is to move from a broad research question to a specific, testable plan. This skill generates the core hypotheses that will define the experimental or observational approach.
*   **Bridging Disparate Findings:** When analysis reveals two or more pieces of evidence that are in tension or seem unrelated; this skill can propose hypotheses that might unify or explain the discrepancy.
*   **Prior to `research_plan` or `experiment_design`:** This skill's output (hypotheses with suggested tests) is the direct, necessary input for downstream planning skills, which will elaborate the suggested tests into full methodologies.

**Upstream Dependencies & Expected Input Format:**
This skill requires structured input about the current state of knowledge. It expects the agent's context (`ctx`) to contain outputs from prior analysis, specifically:
*   A clear articulation of the **research question** or problem space.
*   A summary of **established evidence** (facts, data, accepted theories).
*   A list of **identified gaps, contradictions, or unknowns** (ideally from `gap_analysis`). The input is not raw data but a synthesized analysis stating "We know X, but we don't know Y."

**Edge Cases - When NOT to Use:**
*   **When No Evidence Gaps Exist:** If the `gap_analysis` concludes there are no meaningful unknowns or contradictions, do not force hypothesis generation; the task may be complete.
*   **For Pure Data Generation or Extraction:** Do not use this skill to simply extract facts from a dataset (use `data_analysis`). It is for proposing *new* explanations.
*   **For Final Conclusions:** This skill proposes *questions to be tested*, not final answers. Do not use it to present findings as definitive.
*   **In Place of a Search:** If the gap is a simple factual question (e.g., "What is the melting point of compound Z?"), use a `search` skill, not `hypothesis_gen`.

**Typical Downstream Nodes:**
*   `research_plan`: To develop a comprehensive strategy for testing the generated hypotheses.
*   `experiment_design`: To operationalize a specific `suggested_test` into a detailed protocol.
*   `content_gen` (for a research proposal): To incorporate the hypotheses into a formal document.

## Execution Model

LLM-based

**Prompt file**: `prompts/hypothesis_gen.md`

## Output Contract

AnalysisOutput — hypotheses: [{hypothesis, rationale, testability_score, suggested_test}]

## Constraints

*   **Evidence Anchoring is Mandatory:** Every generated hypothesis must be explicitly and logically rooted in the evidence provided in the context (`ctx`). The `rationale` field must cite specific upstream findings or gaps. **Absolute prohibition on fabrication or introduction of entirely new, unsupported premises.**
*   **Focus on Testability:** The primary evaluation criterion is `testability_score`. Hypotheses must be falsifiable through empirical observation or experiment. Avoid generating broad, philosophical, or untestable conjectures.
*   **Avoid Scope Creep:** Hypotheses must stay within the domain and scale of the original research question. Do not generate hypotheses that would require fundamentally different expertise, resources, or data types than those implied by the upstream context.
*   **Prioritize Quality over Quantity:** The skill should generate a concise, high-quality list (typically 3-5) of the most promising hypotheses. Do not produce an exhaustive laundry list of every possible idea.
*   **Adhere to Output Schema:** The output must be a valid `AnalysisOutput` object with the `hypotheses` list containing dictionaries that exactly match the specified keys (`hypothesis`, `rationale`, `testability_score`, `suggested_test`). `testability_score` must be a numerical value (e.g., 1-5 or 1-10 scale).