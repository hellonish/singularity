# explainer

**Tier**: output  
**Name**: `explainer`  

## Description

Produces accessible, jargon-free explanation for lay audiences.

## When to Use

When audience is 'layperson' or 'student', or plan output_format is 'explainer'.

## Execution Model

LLM-based

**Prompt file**: `prompts/explainer.md`

## Output Contract

OutputDocument — explainer text with plain-language glossary, analogies

## Constraints

- Replace jargon with plain-language equivalents in parentheses on first use
- One analogy per major concept
- Reading level: ~8th grade layperson, ~12th grade student
