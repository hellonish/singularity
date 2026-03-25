# bibliography_gen

**Tier**: output  
**Name**: `bibliography_gen`  

## Description

Formats all cited sources into a bibliography in the appropriate citation style.

## When to Use

Always included as a supporting output node after report_generator or exec_summary.

## Execution Model

LLM-based + CitationRegistry

**Prompt file**: `prompts/bibliography_gen.md`

## Output Contract

OutputDocument — formatted_bibliography string

## Constraints

- Styles: APA 7 (default), Bluebook (legal), IEEE (technical), Vancouver (medical)
- Missing fields → append [incomplete citation — verify manually]
