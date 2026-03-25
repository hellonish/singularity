# exec_summary

**Tier**: output  
**Name**: `exec_summary`  

## Description

The `exec_summary` skill is a specialized output generation module designed to synthesize complex, multi-faceted information into a standardized, high-impact executive summary format. It physically processes the provided input context—which typically includes research findings, analysis results, decision logs, or raw data interpretations—through a structured cognitive distillation pipeline. The agent first extracts the core conclusion or ultimate recommendation, formulating it as an unambiguous "bottom line." It then systematically scans the input evidence to identify, rank, and select the three most salient, diverse, and supportive data points or logical arguments, transforming them into concise, impactful bullet points. Concurrently, the agent performs a critical self-assessment of the analysis to identify a primary limitation, caveat, or assumption that qualifies the findings. Finally, it determines a clear, actionable immediate next step that logically follows from the conclusion. This entire process results in a compact document structured for rapid comprehension by decision-makers, emphasizing clarity, brevity, and actionable insight over exhaustive detail.

## When to Use

- **Primary Scenario**: Use this skill when the `plan` explicitly specifies an `output_format` of `'exec_summary'`. This is the definitive trigger for its application.
- **Secondary Scenario**: Use as a final wrapper for outputs that are highly sensitive, controversial, or require a strong disclaimer. It frames the core findings within a context of limitations and recommended actions.
- **Upstream Dependencies**: This skill MUST be placed downstream of nodes that have completed substantive analysis. It expects as input a comprehensive context containing:
    - A clear conclusion or set of findings from prior analysis (e.g., from `analyze`, `research`, or `synthesize` skills).
    - The evidence or reasoning that led to that conclusion.
    - Information about data sources, confidence levels, or known gaps.
- **Downstream Nodes**: The output of this skill is typically a terminal node in the execution DAG. It is the final, packaged deliverable. In complex workflows, its output (`bottom_line`, `next_step`) could be passed to a `presentation` or `communication` skill for formatting into emails or slide decks.
- **Edge Cases - DO NOT USE**:
    - When the requested output is a detailed report, technical deep-dive, or raw data listing.
    - When the input context is insufficient or highly ambiguous; this skill distills, it does not invent or research.
    - As an intermediate step in a chain of reasoning; it is designed as a final summarization layer.

## Execution Model

LLM-based

**Prompt file**: `prompts/exec_summary.md`

## Output Contract

OutputDocument — {bottom_line, key_evidence[3], limitation, next_step}

## Constraints

- **Strict Length Limit**: The final summary text must not exceed 350 words in total. The Planner must ensure the input context provided is not so voluminous that it would force the LLM to produce an overly verbose summary.
- **Structural Mandate**: The "bottom line" MUST be presented as the very first sentence of the output. Do not include preamble, greetings, or titles.
- **Hallucination Prohibition**: The agent must derive all content (evidence bullets, limitation, next step) strictly from the provided input context. It must not introduce external knowledge, unsupported opinions, or fabricate evidence.
- **Evidence Specificity**: The three `key_evidence` points must be distinct, concrete, and directly traceable to the input. Avoid vague statements like "data suggests" without specifying what the data is.
- **Limitation Scope**: The identified `limitation` must be a genuine constraint from the analysis (e.g., data recency, sample size, scope boundary) and not a generic disclaimer.
- **Actionable Next Step**: The `next_step` must be a concrete, immediate action (e.g., "Approve the budget request," "Conduct a pilot test with Group A," "Request Q3 sales data from finance") and not a vague continuation (e.g., "Analyze further").