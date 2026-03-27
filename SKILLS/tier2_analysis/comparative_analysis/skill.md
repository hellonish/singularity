# comparative_analysis

**Tier**: analysis  
**Name**: `comparative_analysis`  

## Description

This skill performs a structured, multi-dimensional comparison between two or more distinct subjects (e.g., products, technologies, strategies, companies, methodologies, or entities). It is a cognitive analysis process that moves beyond simple listing to a rigorous, axis-by-axis evaluation. The skill physically ingests descriptive data about each subject and systematically processes it through a defined analytical framework. The core cognitive process involves: 1) **Axis Identification & Definition**: Determining the relevant, comparable criteria (axes) for evaluation based on the subjects' domains and the user's implicit or explicit goals. 2) **Data Mapping & Normalization**: For each subject, extracting or inferring relevant data points and mapping them onto the defined axes, often transforming qualitative descriptions into comparable qualitative or semi-quantitative values. 3) **Axis-wise Evaluation**: Conducting a side-by-side comparison for each axis, assessing the relative performance, strength, or characteristic of each subject. 4) **Synthesis & Judgment**: For each axis, determining if a clear "winner" or superior subject can be identified based on the mapped values, while explicitly noting any caveats, uncertainties, or data gaps that preclude a definitive judgment. The final output is a structured table of findings, transforming raw, often unstructured input data into a clear, decision-ready comparative matrix.

## When to Use

- **Specific Scenarios**:
    - **Decision Support**: When a user is evaluating multiple options and needs a balanced, criteria-based breakdown to inform a choice (e.g., "Compare AWS Lambda vs. Azure Functions vs. Google Cloud Functions for our serverless backend," "Analyze the investment potential of Company A vs. Company B").
    - **Feature/Product Analysis**: When contrasting the specifications, capabilities, or performance metrics of competing products, tools, libraries, or services.
    - **Strategic Planning**: When assessing different strategic approaches, business models, or technical architectures against a set of organizational goals or constraints.
    - **Research Synthesis**: When consolidating information from multiple sources about different entities to highlight their relative strengths, weaknesses, and differentiating factors.
- **Upstream Dependencies & Input Format**:
    - This skill **requires** upstream nodes (like `information_gathering`, `research`, or `data_retrieval`) to have provided sufficiently detailed, descriptive data on **each subject** to be compared. The input is typically unstructured or semi-structured text (e.g., research summaries, product descriptions, extracted specifications). The skill expects data for all subjects to be present in the context; it cannot proceed if data for one or more subjects is completely missing.
    - The Planner should ensure the preceding steps have collected information on a **common set of relevant attributes** for the subjects, even if the data is incomplete for some axes.
- **Edge Cases - When NOT to Use**:
    - **Single Subject Analysis**: Do not use if the task involves deep analysis of only one entity without comparison to another. Use `deep_research_analysis` or `summarization` instead.
    - **Pure Ranking or Scoring**: Do not use if the task is solely to rank a list based on a single, well-defined metric. A simpler `evaluation` or calculation skill may suffice.
    - **Generating Pros/Cons Lists**: Do not use if the required output is simple, unstructured lists of advantages and disadvantages for individual items without a structured, axis-by-axis comparison.
    - **Insufficient Data**: Avoid invoking if upstream nodes have failed to gather meaningful descriptive data for at least two subjects. The skill will output mostly "insufficient data" caveats, providing little value.
- **Downstream Nodes**:
    - The structured output of this skill is typically fed into: 1) **`recommendation`** skills, which use the comparative matrix to synthesize a final suggested option. 2) **`report_generation`** or `executive_summary` skills, which incorporate the comparative table into a larger document. 3) **Decision nodes** in the execution DAG that branch based on the identified "winners" for key axes.

## Execution Model

LLM-based

**Prompt file**: `prompts/comparative_analysis.md`

## Output Contract

AnalysisOutput — findings: [{axis, values_per_subject, winner_if_any, caveat}]

## Constraints

- **Explicit Insufficiency Declaration**: The most critical constraint is to **note explicitly when data is insufficient to compare on a given axis**. The LLM must not hallucinate comparisons based on missing data. For each axis where comparable information is absent for one or more subjects, the `values_per_subject` must reflect the known data, and the `caveat` field must clearly state the data gap.
- **Axis Relevance & Scope**: The identified axes must be directly relevant to the subjects and the user's likely intent. Avoid creating trivial, overly generic (e.g., "popularity"), or non-comparable axes. The analysis must remain within the scope of the provided data and the subject domain; do not introduce external, unverified knowledge as fact.
- **Avoiding Hallucination of Values**: Under no circumstances should the LLM invent specific numerical scores, ratings, or detailed qualitative judgments that are not directly supported or strongly implied by the input text. The `values_per_subject` should be concise summaries or extractions from the source data.
- **Balanced Treatment**: The comparison must be objective and balanced. The skill should not inherently favor the first-listed subject or demonstrate bias unless the input data unequivocally supports a superiority claim.
- **Output Structure Fidelity**: The output must strictly adhere to the `AnalysisOutput` contract. Each finding must be a complete dictionary with the four specified keys. The `winner_if_any` field must be `null` if no clear superior subject can be determined for that axis.
- **Token Management**: The prompt and processing must be designed to handle comparisons of up to 4-5 subjects across 5-7 axes without exceeding context windows. For larger comparisons, the Planner should consider breaking the task into multiple, focused comparative analyses.