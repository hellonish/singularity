# visualization_spec

**Tier**: output  
**Name**: `visualization_spec`  

## Description

This skill is a specialized cognitive and data transformation process that converts structured data and analytical insights into a precise, machine-readable chart specification. It does NOT render or generate any visual image, bitmap, or graphical file. Instead, it acts as a high-level design and instruction layer, performing the following physical and logical operations:

1.  **Cognitive Analysis & Intent Mapping**: The agent analyzes the provided data context, narrative goals, and key findings to determine the most effective visual metaphor for communication. It maps abstract concepts (e.g., "trend over time," "comparison between categories," "distribution," "correlation") to a concrete, supported chart type.
2.  **Data Structure Translation**: It interprets the shape and semantics of the input data (e.g., lists of records, time-series arrays, aggregated summary statistics) and translates them into the formal structural components of a chart specification: `x_axis`, `y_axis`, and `series`. This involves identifying which data fields correspond to categorical labels, quantitative values, temporal dimensions, or series groupings.
3.  **Specification Authoring**: The skill authors a complete JSON object that serves as a blueprint for a downstream rendering engine. This includes defining a concise, descriptive `title`, configuring axis labels with units if necessary, structuring series data correctly, and adding optional `notes` for the renderer (e.g., highlighting a specific data point, suggesting a color scheme for a series).
4.  **Abstraction & Encapsulation**: It abstracts away specific plotting library syntax (like Matplotlib or Vega-Lite code) and delivers a platform-agnostic contract. The output is purely declarative, describing *what* to visualize, not *how* to implement it programmatically.

## When to Use

Use this skill in the following specific scenarios:

*   **Upstream Dependencies Exist**: The skill must be invoked **after** nodes that have produced clean, structured, and analyzed data. Typical upstream inputs include:
    *   A `data_analysis` node that has summarized trends, comparisons, or correlations.
    *   A `data_transformation` or `data_summary` node that has aggregated, filtered, or prepared a dataset specifically for presentation.
    *   A context where the narrative (e.g., from a `report_planning` node) explicitly calls for a chart to illustrate a point.
*   **Downstream Rendering is Available and Planned**: This skill is **only** valuable when a subsequent node in the DAG (e.g., a `code_interpreter` skill, a dedicated `chart_renderer` service, or a front-end application) is configured to consume its JSON output contract and execute the actual rendering. It is the penultimate step before visualization generation.
*   **The Communication Goal is Visual Summarization**: When the core task is to transform complex quantitative or relational data into an intuitive visual form to support a conclusion, reveal a pattern, or simplify a comparison for human consumption.
*   **The Data Warrants It**: The dataset has clear dimensions (at least one categorical, temporal, or quantitative axis) and values suitable for encoding in a visual channel (height, length, position, color intensity).

**Edge Cases - When NOT to Use This Skill:**

*   **When Raw Image Output is the Direct Goal**: If the task is "generate a chart PNG," do not use this skill in isolation. It must be paired with a renderer.
*   **For Pure Textual or Tabular Reporting**: If the analysis is best presented in paragraphs or a simple markdown table without graphical encoding, use `narrative_writing` or `table_generation` skills instead.
*   **With Unstructured or Unanalyzed Data**: Do not call this skill on raw, uncleaned text or data that hasn't been processed into a clear structured format (like a list of dictionaries or a pandas DataFrame description). It requires interpreted data.
*   **If the Required Chart Type is Not Supported**: If the narrative absolutely requires a chart type outside the constrained list (e.g., a network graph, a Sankey diagram, a 3D plot), this skill cannot be used.

**Typical Downstream Nodes:**
*   A `code_interpreter` skill that takes the spec and writes Python code (e.g., using Matplotlib, Plotly, Seaborn) to create the image.
*   A system process that passes the spec to a dedicated visualization service or library.
*   A front-end component that renders the chart using a JavaScript library like D3.js or Chart.js, based on the provided spec.

## Execution Model

LLM-based

**Prompt file**: `prompts/visualization_spec.md`

## Output Contract

OutputDocument — JSON spec: {chart_type, title, x_axis, y_axis, series, notes}

## Constraints

*   **Strictly Declarative, Non-Executable Output**: The output must **ONLY** be the JSON specification object. It must **NOT** contain any code snippets, library-specific commands, image data, or base64 strings. The skill's sole purpose is to define the visualization parameters.
*   **Limited Chart Type Vocabulary**: The `chart_type` field is **strictly constrained** to the following set: `bar` | `line` | `scatter` | `table` | `timeline` | `heatmap`. The LLM must not hallucinate or invent other chart types (e.g., `pie`, `area`, `histogram`, `boxplot`). If the data suggests an unsupported type, the LLM must select the closest valid analogue (e.g., use a `bar` chart for a distribution instead of a `histogram`).
*   **No Visual Design Hallucination**: The spec should avoid prescribing exact visual details beyond the core structure. Do not specify precise hex colors, pixel dimensions, font families, or absolute positioning unless critically necessary and placed in the `notes` field. The rendering agent handles aesthetic implementation.
*   **Input Scope Limitation**: The skill must base its specification **solely** on the data and context provided in the current task. It must not retrieve, infer, or hallucinate external data points to populate the chart series. All data for `x_axis`, `y_axis`, and `series` must be derivable from the given input.
*   **Schema Adherence**: The output JSON must perfectly match the expected `OutputDocument` schema with the specified fields. The `notes` field is optional, but all others are required.