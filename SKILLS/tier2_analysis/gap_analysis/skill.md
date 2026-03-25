# gap_analysis

**Tier**: analysis  
**Name**: `gap_analysis`  

## Description

This skill performs a systematic, comparative analysis between the current state of a research plan's execution and the defined termination signal. It is a critical cognitive function that identifies deficiencies, omissions, and unmet criteria within the research trajectory. The agent physically processes the plan's execution history (including all executed nodes, their outputs, and the data retrieved) and the `plan.metadata.termination_signal`. It then applies a structured reasoning process to map what has been accomplished against what was *required* to be accomplished for the plan to be considered complete. The core data transformation involves converting a linear history of actions and a goal statement into a structured list of actionable gaps, each characterized by its description, severity, and a concrete suggestion for remediation. This is not a simple checklist comparison; it involves interpreting the intent behind the termination signal, assessing the sufficiency and relevance of gathered information, and judging where the research logic has fallen short or diverged from the required end state.

## When to Use

- **Primary Scenario**: After at least one full cycle of information retrieval and synthesis (e.g., after `retrieve_docs`, `summarize`, or `synthesize` nodes have been executed). The skill requires substantive execution history to analyze; using it on a fresh plan with no results yields trivial gaps.
- **Upstream Dependencies**: This skill **must** be executed downstream of nodes that generate the data it analyzes. It expects as input a populated `plan` object containing:
    1. `plan.metadata.termination_signal`: A clear, textual description of the conditions for plan completion.
    2. `plan.state.execution_history`: A sequential record of executed skill nodes, their parameters, and most importantly, their `AnalysisOutput` or `DataOutput` results. The quality of gap analysis is directly dependent on the richness of this history.
- **Triggering Replanning**: The primary downstream use of this skill's output is as the direct input to a `replanning` skill. The identified gaps are the specific issues the replanning agent must address by adding, removing, or modifying future nodes in the plan DAG.
- **Edge Cases - When NOT to Use**:
    - **Do NOT use** at the very beginning of a plan before any substantive research nodes have run. The gaps will merely restate the termination signal.
    - **Do NOT use** if the `termination_signal` is missing, overly vague, or merely states "when the user is satisfied." The analysis requires a concrete, analyzable target.
    - **Do NOT use** as a substitute for `synthesize` or `summarize`. This skill analyzes coverage against a goal; it does not synthesize new knowledge from existing information.
    - **Avoid using** in a tight loop without intermediate execution. Repeated gap analysis without new data between cycles is redundant.

## Execution Model

LLM-based

**Prompt file**: `prompts/gap_analysis.md`

## Output Contract

AnalysisOutput — gaps: [{gap_description, severity, suggested_node}]

## Constraints

1. **Mandatory Comparison Target**: The analysis **must** be rigorously anchored to the contents of `plan.metadata.termination_signal`. Every identified gap must be traceable to a specific, unmet aspect of this signal. Do not hallucinate requirements not present in the signal.
2. **Severity Classification**: The `severity` field is **strictly limited** to one of three discrete values: `critical`, `moderate`, or `minor`. Define these clearly in reasoning:
    - `critical`: A gap that directly prevents the plan from satisfying the core intent of the termination signal. Missing a key piece of mandatory information or addressing a fundamental misconception.
    - `moderate`: A gap where coverage is incomplete, ambiguous, or lacks depth on an important sub-topic necessary for a robust conclusion.
    - `minor`: A gap involving clarification, additional supporting evidence, or tangential details that would improve the result but are not essential for meeting the primary signal.
3. **Actionable Suggestions**: Each `suggested_node` must be a **plausible, executable skill name** (e.g., `retrieve_docs`, `analyze_data`, `compare_arguments`) that, if executed, would directly address the identified gap. Vague suggestions like "research more" are invalid.
4. **Scope Limitation**: The analysis **must only** consider information within the provided plan execution history and termination signal. It must not:
    - Introduce external knowledge or assumptions about the topic.
    - Speculate on data that *might* exist but hasn't been retrieved.
    - Critique the plan structure itself unless it directly causes a failure to meet the termination signal.
5. **Output Focus**: The output is **exclusively** the list of gaps. Do not include summaries of what *has* been covered, general commentary, or replanning logic. The `AnalysisOutput` must be cleanly structured for programmatic consumption by the downstream replanner.
6. **Token Awareness**: When processing extensive execution histories, prioritize the most relevant outputs (e.g., synthesis conclusions) for comparison. The LLM must distill the history's essence rather than exhaustively recounting it, to stay within context window limits.