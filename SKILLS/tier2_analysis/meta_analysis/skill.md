# meta_analysis

**Tier**: analysis  
**Name**: `meta_analysis`  

## Description

Aggregates effect sizes from multiple clinical studies (medical domain only).

## When to Use

Medical systematic reviews with ≥3 comparable studies.

## Execution Model

LLM-based

**Prompt file**: `prompts/meta_analysis.md`

## Output Contract

AnalysisOutput — {pooled_effect, heterogeneity_i2, study_count, forest_plot_data}

## Constraints

- If < 3 studies → return {insufficient_studies: true}, no pooled estimate
