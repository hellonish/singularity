# report_generator

**Tier**: output  
**Name**: `report_generator`  

## Description

Generates a full research report with executive summary, findings, methodology, limitations, and references.

## When to Use

Final output node for 'report' output_format in plan metadata.

## Execution Model

LLM-based

**Prompt file**: `prompts/report_generator.md`

## Output Contract

OutputDocument — sections: exec_summary, methodology, findings, limitations, references

## Constraints

- Length targets: layperson 600w, student 1500w, practitioner 2000w, expert 3000w, executive 400w
- Must disclose all PARTIAL/FAILED node coverage gaps
- Inline citations in [Author YYYY] format throughout
