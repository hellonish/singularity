# meta_analysis

**Tier**: analysis  
**Name**: `meta_analysis`  

## Description

This skill performs a quantitative meta-analysis, a rigorous statistical procedure that synthesizes numerical results from multiple independent clinical studies within the medical domain. It physically ingests structured data on effect sizes and their measures of precision (e.g., confidence intervals, standard errors) from a collection of comparable studies. The cognitive process involves first assessing the clinical and methodological homogeneity of the provided studies to ensure a valid synthesis is possible. It then applies statistical models to aggregate the individual study estimates into a single, more precise summary effect size (pooled estimate). A critical component of this process is the quantification of heterogeneity—the degree of variation in effect sizes across studies beyond chance—using the I² statistic, which is calculated and interpreted (e.g., 0-40%: might not be important; 30-60%: moderate heterogeneity; 50-90%: substantial heterogeneity; 75-100%: considerable heterogeneity). The skill also prepares the foundational data required for generating a forest plot, a standard visualization in meta-analyses that displays individual study estimates and the pooled result with confidence intervals. This is not a qualitative summary but a precise, model-driven quantitative synthesis.

## When to Use

- **Specific Scenarios**:
    1. Conducting a systematic review and meta-analysis for a clinical research question (e.g., "What is the efficacy of Drug X vs. placebo on mortality in Condition Y?").
    2. Updating a previous meta-analysis with new trial data to refine the pooled effect estimate.
    3. Performing subgroup or sensitivity analyses within a larger review to explore sources of heterogeneity.
    4. Generating the statistical core for a clinical guideline or health technology assessment report.

- **Upstream Dependencies & Input Data Format**:
    This skill **must** be preceded by a data extraction or collection skill (e.g., `data_extraction`, `study_aggregation`) that provides a clean, structured list of study findings. The expected input is an array of study objects, where each object **must contain**:
    - `study_id`: A unique identifier (e.g., "Smith_2020").
    - `effect_size`: A numerical value for the point estimate (e.g., Odds Ratio of 0.85, Hazard Ratio of 1.2, Mean Difference of -5.2).
    - `ci_lower` and `ci_upper`: The lower and upper bounds of the 95% confidence interval for the effect size.
    - `weight` (optional): A pre-calculated weight for the study (e.g., inverse variance). If not provided, the skill will calculate weights based on confidence interval width.
    - Additional metadata like `population`, `intervention`, `outcome` is helpful for homogeneity assessment but not strictly required for calculation.

- **Edge Cases - When NOT to Use**:
    1. **Qualitative Synthesis**: Do not use if the goal is a narrative summary without statistical pooling.
    2. **Non-Clinical Data**: Do not use for synthesizing studies from engineering, social sciences, or economics unless explicitly adapted; the domain constraint is medical.
    3. **Incomparable Studies**: Do not use if the studies measure fundamentally different outcomes (e.g., mortality vs. quality of life) or use incompatible effect measures (e.g., mixing Odds Ratios with Mean Differences without conversion).
    4. **Extreme Heterogeneity**: If an initial check reveals overwhelming statistical heterogeneity (I² > 90%), caution is required, and the skill may produce a misleading summary. Consider a random-effects model and note the limitation, or do not pool.
    5. **Single Study or Two Studies**: As per constraints, it will not compute a pooled estimate.

- **Downstream Nodes**:
    1. `report_generation` or `evidence_synthesis`: To incorporate the meta-analysis results (pooled effect, I²) into a comprehensive narrative report.
    2. `visualization_agent` (or similar): To consume the `forest_plot_data` output and produce a publication-ready forest plot visualization.
    3. `sensitivity_analysis`: To re-run the meta-analysis under different assumptions (e.g., fixed-effect vs. random-effects model, excluding outliers).
    4. `publication_bias_assessment`: To follow up with statistical tests (e.g., Egger's test) if the number of studies is sufficient.

## Execution Model

LLM-based

**Prompt file**: `prompts/meta_analysis.md`

## Output Contract

AnalysisOutput — {pooled_effect, heterogeneity_i2, study_count, forest_plot_data}

## Constraints

1.  **Minimum Study Count**: The analysis is only statistically valid and will only be performed if **three (3) or more** comparable studies are provided in the input. If the input contains fewer than 3 studies, the skill **must not attempt** any pooling calculation. It **must strictly return** `{insufficient_studies: true}` within the output structure, with `pooled_effect` and `heterogeneity_i2` set to `null` or omitted. This is a non-negotiable rule.
2.  **Domain Limitation**: Restricted to the **medical/clinical domain** (e.g., RCTs, cohort studies on patient outcomes, diagnostic accuracy studies). The LLM must not hallucinate or extrapolate methods from other fields (e.g., genomics, machine learning meta-analysis) unless the input data is explicitly tagged as such, which it should not be for this skill's intended use.
3.  **Input Data Fidelity**: The skill must rely **exclusively** on the numerical data (`effect_size`, `ci_lower`, `ci_upper`) provided for each study. It must not invent, impute, or guess missing confidence intervals or effect sizes. If a study entry is missing critical numerical fields, that study must be excluded from the analysis, and a note should be made.
4.  **Statistical Model Transparency**: The LLM must clearly state in its reasoning (though not in the final contract output) which statistical model was applied (typically a fixed-effect or random-effects model based on the heterogeneity assessment). The choice of model must be justified by the calculated I² value or a pre-specified plan.
5.  **Avoiding Hallucination of Methodology**: The LLM must not invent complex statistical procedures (e.g., network meta-analysis, multivariate meta-regression) unless the prompt specifically directs it and the input data structure supports it. The core function is a standard inverse-variance weighted meta-analysis.
6.  **Token/Computation Limits**: For very large numbers of studies (e.g., >50), the LLM's context window may be strained if full study texts are passed. The input to this skill should be pre-processed into the minimal structured data format described above. The skill itself performs lightweight calculations and should not be tasked with re-extracting data from full-text articles.