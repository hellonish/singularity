# causal_analysis

**Tier**: analysis
**Name**: `causal_analysis`

## Description

This skill performs a rigorous, structured analysis to identify and evaluate causal relationships within a given dataset or body of evidence. It moves beyond identifying simple correlations by applying established causal inference frameworks (e.g., Bradford Hill criteria, counterfactual reasoning) to assess whether one variable (the cause) is responsible for changes in another (the effect). The core cognitive process involves: 1) **Identifying Candidate Relationships**: Parsing the provided context to extract potential cause-effect pairs, often signaled by language implying influence, change, or impact. 2) **Evidence Categorization & Scrutiny**: For each candidate claim, it systematically classifies the supporting evidence into a strict hierarchy of study types (RCT, observational, mechanistic, expert_opinion) and evaluates its methodological rigor. 3) **Confounding & Bias Analysis**: It actively searches for and documents potential confounding variables, reverse causality, selection bias, or other threats to internal validity that could create the illusion of causation. 4) **Strength Assessment**: It synthesizes the quality, consistency, and specificity of the evidence to assign a qualitative strength rating to the causal claim. The physical output is a structured JSON object that transparently documents this analytical journey, separating robust causal conclusions from mere associations and highlighting critical gaps in evidence.

## When to Use

- **Specific Scenarios**:
    - When analyzing experimental results (e.g., A/B tests, clinical trial data) to confirm the treatment caused the observed outcome.
    - When evaluating observational studies (e.g., epidemiological data, user behavior logs) to determine if a linked factor is likely causal or merely correlated.
    - When reviewing scientific literature or technical reports that make claims of influence or impact.
    - When the problem statement includes keywords/phrases like "root cause," "driven by," "impact of X on Y," "effect of," "leads to," or "why did this happen?".
- **Upstream Dependencies**:
    - This skill typically requires well-structured, summarized data or text as input. The ideal upstream node provides a clear **context** containing the variables of interest and the available evidence (e.g., output from `data_summarization`, `literature_review`, or `problem_decomposition`). It expects this input to describe relationships, present data points, or state claims that need causal vetting.
- **When NOT to Use (Edge Cases)**:
    - **Do NOT use** for purely descriptive tasks like summarizing trends or calculating correlation coefficients without the intent to infer causation.
    - **Do NOT use** when the input contains only a single data point or anecdote with no comparative evidence.
    - **Avoid using** for predicting future events (use `forecasting`), optimizing parameters (use `ab_test_analysis`), or diagnosing faults in systems (use `root_cause_analysis` which may call this skill as a sub-component).
    - **Do NOT use** if the request is to *establish* causation through new experimentation; this skill *analyzes* existing evidence.
- **Downstream Nodes**:
    - The structured output is typically consumed by `hypothesis_generation` to formulate new testable predictions.
    - It feeds into `reporting` or `executive_summary` skills to present evidence-based conclusions.
    - It can inform `intervention_recommendation` by validating which levers are causally effective.

## Execution Model

LLM-based

**Prompt file**: `prompts/causal_analysis.md`

## Output Contract

AnalysisOutput — claims: [{claim, evidence_type, confounders_noted, strength}]

## Constraints

- **Evidence Type Hierarchy**: The `evidence_type` field MUST be strictly one of: `RCT` (Randomized Controlled Trial), `observational`, `mechanistic` (biological/engineering pathway explanation), or `expert_opinion`. This is a mandatory classification for each claim.
- **RCT Evidence Mandate**: If a definitive causal claim is made (e.g., "X causes Y") and the highest available evidence is NOT `RCT`, you MUST explicitly note the absence of RCT evidence within the `findings` or a relevant field to highlight the evidence limitation. Do not allow the claim's strength to be overstated.
- **Hallucination Prohibition**: You MUST NOT invent or assume evidence that is not present in the provided input context. If evidence for a relationship is absent, state that explicitly; do not infer it.
- **Scope Limitation**: Analysis MUST be confined strictly to the variables and data presented in the input context. Do not introduce external common knowledge or broad societal factors unless they are directly referenced in the provided material.
- **Confounder Documentation**: You MUST actively list potential confounding variables for observational evidence, even if they are not definitively proven. The absence of discussed confounders should also be noted.
- **Strength Assessment Rationale**: The assigned `strength` (e.g., "strong," "moderate," "weak," "speculative") must be directly justifiable by the categorized `evidence_type` and the documented `confounders_noted`.