# visualization_spec

**Tier**: output  
**Name**: `visualization_spec`  

## Description

Produces a machine-readable chart specification (does NOT render).

## When to Use

When data warrants visual presentation and downstream rendering is available.

## Execution Model

LLM-based

**Prompt file**: `prompts/visualization_spec.md`

## Output Contract

OutputDocument — JSON spec: {chart_type, title, x_axis, y_axis, series, notes}

## Constraints

- chart_type: bar | line | scatter | table | timeline | heatmap
- Does NOT produce an image
