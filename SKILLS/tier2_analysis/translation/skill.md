# translation

**Tier**: analysis  
**Name**: `translation`  

## Description

Translates source content to the plan's output_language.

## When to Use

When plan.metadata.multilingual=true or source language ≠ output_language.

## Execution Model

Tool-based (LibreTranslate primary, Google Translate fallback)

## Output Contract

AnalysisOutput — {original, translated, source_lang, target_lang, confidence}

## Constraints

- confidence < 0.80 → append [low-confidence translation] to output
