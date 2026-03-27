# statistical_analysis

**Tier**: analysis  
**Name**: `statistical_analysis`  

## Description

This skill performs a comprehensive statistical analysis on extracted numerical tabular data. It physically ingests structured data, typically in the form of a list of dictionaries, a pandas DataFrame representation, or a two-dimensional array, where rows represent observations and columns represent variables. The core cognitive process involves a hybrid approach: first, the LLM interprets the structure and semantic meaning of the data (e.g., identifying column headers, data types, and units), and then precise Python computations are executed to derive objective statistical measures. The skill applies specific data transformations including type coercion (ensuring numerical values are cast to integers or floats), handling of missing or non-numeric entries (typically by exclusion from calculations), and the aggregation of observations per variable. For each identified numerical variable, it systematically calculates a standard set of descriptive statistics: the mean (arithmetic average), median (middle value), range (difference between maximum and minimum), and count of valid observations (n). It also captures and preserves the unit of measurement associated with each variable, if provided in the source data. The output is a clean, structured summary designed to characterize the central tendency, dispersion, and sample size for every quantitative column in the dataset.

## When to Use

- **Specific Scenarios**:
    1. After `data_extraction` or `web_scrape` has successfully parsed a table, chart, or list of numerical values from a document, webpage, or report.
    2. When the upstream data is confirmed to contain quantitative columns (e.g., prices, temperatures, scores, counts, percentages, measurements).
    3. As a foundational analysis step before more complex operations like `trend_identification`, `comparative_analysis`, or `hypothesis_testing`.
    4. To provide a factual, numerical summary for inclusion in a `report_generation` or `executive_summary` skill.

- **Upstream Dependencies & Expected Input**:
    - **Primary Dependency**: This skill almost always follows `data_extraction`. It expects the output of that skill: structured, tabular data. The ideal input format is a list of dictionaries (where keys are column names) or an explicit mention of a DataFrame with column headers and rows.
    - **Required Input Data Format**: The input must clearly specify column/variable names and their corresponding values. The presence of numerical data is mandatory. A snippet or explicit description of the table structure should be provided by the upstream node.

- **Edge Cases - When NOT to Use**:
    1. **Non-Numerical Data**: If the extracted table consists solely of textual, categorical, or date data without quantifiable numerical columns. Use `text_analysis` or `categorization` instead.
    2. **Raw, Unstructured Text**: If the data is still in prose paragraphs or unstructured lists. Ensure `data_extraction` runs first.
    3. **Single Data Points**: If the dataset contains only one observation per variable, statistics like mean and median are valid but range is zero and not informative. Consider if analysis is needed.
    4. **Pre-Analyzed Data**: If the input already contains computed statistics (e.g., "the report states the average is 10"), this skill is redundant.
    5. **Image or Graph Data**: Do not use for raw images or plots. Use `chart_parsing` or `image_data_extraction` upstream first.

- **Downstream Nodes**:
    - `trend_identification`: To spot patterns over time or across groups using the statistical baseline.
    - `comparative_analysis`: To compare statistics between two or more distinct datasets or groups.
    - `anomaly_detection`: To identify outliers based on the calculated statistical ranges and distributions.
    - `report_generation` / `executive_summary`: To embed the statistical summary into a narrative format.

## Execution Model

LLM-based + Python computation

**Prompt file**: `prompts/statistical_analysis.md`

## Output Contract

AnalysisOutput — stats: [{variable, mean, median, range, n, unit}]

## Constraints

- **Never Fabricate Statistics**: All output numbers must be the direct result of computational operations on the provided input data. The LLM must not infer, estimate, or hallucinate statistical values based on pattern recognition or external knowledge. If a calculation cannot be performed due to data issues, state this explicitly.
- **State Explicitly if Data is Insufficient**: If the input contains no numerical columns, all values are non-numeric, or there are fewer than two valid observations for a variable (making range trivial), the skill must output a clear declaration of insufficiency rather than forcing a calculation.
- **Token Limit Awareness**: The input dataset could be large. The skill should summarize or sample if needed to stay within context windows, but must note if sampling was applied. Prefer computation on the full dataset when feasible via Python.
- **Scope Limitation**: This skill is purely descriptive. It does NOT perform inferential statistics (t-tests, ANOVA, correlations), predictive modeling, or causal analysis. Do not attempt to interpret the "significance" or "meaning" of the statistics beyond their mathematical definition.
- **Unit Integrity**: The unit field must be extracted directly from the source data (e.g., column header like "Temperature (°C)"). If no unit is discernible, the unit field should be an empty string or "N/A". Do not guess or assume units.
- **Variable Identification**: Analyze only columns explicitly presented as numerical. Do not attempt to create derived variables (e.g., ratios of two columns) unless that is the explicit, pre-calculated column in the input.