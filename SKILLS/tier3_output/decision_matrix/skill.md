# decision_matrix

**Tier**: output  
**Name**: `decision_matrix`  

## Description

This skill performs a sophisticated, multi-step cognitive process to transform a complex decision scenario into a structured, actionable, and conditional analysis. It physically generates a comprehensive markdown table (the matrix) that systematically compares multiple options or courses of action against a defined set of critical evaluation criteria. The core cognitive process involves: 1) **Decomposition**: Breaking down the user's query or the provided context into distinct, viable options and relevant, weighted decision factors (e.g., cost, risk, time, strategic alignment, ethical impact). 2) **Evaluation**: For each option-criterion pair, it performs a conditional analysis, scoring or describing the option's performance, and explicitly states the assumptions or data underlying that judgment. 3) **Synthesis**: It aggregates these discrete evaluations to formulate a final, nuanced recommendation that is strictly contingent on stated conditions, never absolute. The primary data transformation is from unstructured problem descriptions or comparative data into a highly organized, scannable matrix format supplemented by explicit conditional logic, caveats, and a sensitivity analysis where appropriate.

## When to Use

- **Specific Scenarios**:
    - When a user is faced with a multi-faceted choice between several strategic options (e.g., "Should we build, buy, or partner for this software?").
    - In comparative analysis requests within legal (e.g., pleading strategies), financial (e.g., investment portfolio choices), product management (e.g., feature prioritization), and business strategy (e.g., market entry approaches) domains.
    - When the upstream plan explicitly specifies `output_format: 'decision_matrix'`.
    - When the decision hinges on multiple variables where the "best" choice changes based on different priorities or future states (e.g., "Choose a cloud provider based on cost vs. performance vs. compliance needs").

- **Upstream Dependencies**:
    - This skill expects well-structured input. Ideally, upstream nodes (like a `query_analyzer` or `research` skill) should have already provided a clear problem statement, a list of potential options (or the raw data to derive them), and the key decision criteria. The input should be in a coherent textual format that details the context of the decision.

- **When NOT to Use (Edge Cases)**:
    - For simple, binary yes/no questions with no alternative paths or evaluation dimensions.
    - When the user requests a single, definitive answer without exploration of alternatives.
    - For generating implementation steps or project plans (use `action_plan` or `project_charter`).
    - If the required data for evaluating options against criteria is completely absent and cannot be reasonably inferred.
    - For purely creative tasks like story generation or open-ended brainstorming.

- **Downstream Nodes**:
    - The output is typically a final-tier output for user consumption. However, it can feed into:
        - A `presentation` skill to format the matrix into slides.
        - An `executive_summary` skill to distill the key conditional recommendation.
        - A `validation` skill to have a second agent review the logical consistency of the conditions and caveats.

## Execution Model

LLM-based

**Prompt file**: `prompts/decision_matrix.md`

## Output Contract

OutputDocument — {matrix_table (markdown), recommendation, conditions, caveats}

## Constraints

- **Conditional Logic Mandate**: The recommendation must NEVER be an unconditional "you should do X." It must ALWAYS be phrased as a conditional statement: "**If** [primary condition A] and [secondary condition B] are true and prioritized, **then** [Option Y] is recommended because...". The matrix must support this by showing how option superiority shifts with different criterion weights.
- **Sensitivity Disclaimer**: For any analysis touching medical advice, legal strategy, or significant financial decisions, a mandatory, prominent disclaimer must be included in the caveats section. It must state that the output is for informational purposes only, is based on provided data, and does not constitute professional advice. It must urge consultation with a qualified professional.
- **Avoid Hallucination of Data**: Do not invent specific numerical scores, financial figures, or performance metrics unless they are explicitly provided or are trivial, common-knowledge estimates. Prefer qualitative descriptors (e.g., "High Cost," "Moderate Risk") backed by stated reasoning.
- **Scope Limitation**: The analysis must be strictly confined to the options and criteria derived from the user's query and provided context. Do not introduce novel, out-of-scope options or highly speculative external factors without clear justification and labeling them as such.
- **Structural Integrity**: The `matrix_table` must be valid, well-formatted markdown that renders correctly. It should include clear headers for Options (rows) and Criteria (columns), with cells containing the evaluation text.
- **Caveats Exhaustiveness**: The `caveats` section must proactively address the limitations of the analysis, including time-sensitivity of data, inherent biases in the evaluation criteria, and the impact of uncertain future events.