# translation

**Tier**: analysis  
**Name**: `translation`  

## Description

This skill performs the physical and cognitive operation of converting textual content from a source language into a specified target language. It is a core data transformation node that operates on extracted text, ensuring the semantic meaning, tone, and intent of the original content are preserved as accurately as possible within the constraints of automated translation. The process begins by receiving text input, explicitly identifying its language (if not provided), and selecting the optimal translation engine based on availability and required language pair support. It then executes the translation via API calls, applying post-processing to handle formatting artifacts and assess the quality of the output. The cognitive process involves not just literal word-for-word substitution but contextual analysis to resolve ambiguities, handle idioms, and maintain grammatical structure in the target language. The final output is a structured bilingual dataset containing the original text, its translation, and metadata about the translation process.

## When to Use

- **Primary Scenarios**:
    1. The plan's `metadata.multilingual` flag is explicitly set to `true`.
    2. The detected or provided language of the source content (`source_lang`) does not match the plan's `output_language`.
    3. Upstream nodes (like `text_extraction` or `summarization`) have produced text that needs to be localized for a downstream audience or process.
    4. Preparing content for a final `synthesis` or `writing` node that requires all inputs to be in a consistent language.

- **Upstream Dependencies & Expected Input**:
    - This skill typically requires an upstream node to provide the text to be translated. The expected input format is a string of text, often contained within an object from a previous analysis step (e.g., `AnalysisOutput.text` or `AnalysisOutput.content`).
    - Ideally, the input includes a `source_lang` property (an ISO 639-1 code like 'en', 'es', 'fr'). If absent, the skill will attempt auto-detection, which may slightly reduce confidence.
    - The plan must have a defined `output_language` (e.g., `plan.output_language = 'es'`).

- **Downstream Nodes**:
    - `summarization`, `sentiment_analysis`, `keyword_extraction`, or other analysis skills that operate on the translated text.
    - `synthesis` or `writing` nodes that compile or present the final output in the target language.
    - Any node requiring linguistically uniform input for coherent processing.

- **Edge Cases & When NOT to Use**:
    - **DO NOT USE** if the source text is already in the plan's `output_language`. This is wasteful and introduces unnecessary noise.
    - **DO NOT USE** for translating code, programming syntax, or structured data fields (like JSON keys or database IDs). This skill is for natural language prose.
    - **AVOID** using on extremely short text fragments (single words without context) or extremely long documents exceeding the translation engine's context window; consider chunking upstream first.
    - **DO NOT ACTIVATE** if the required language pair (source->target) is not supported by the available translation backends.

## Execution Model

Tool-based (LibreTranslate primary, Google Translate fallback)

## Output Contract

AnalysisOutput — {original, translated, source_lang, target_lang, confidence}

## Constraints

- **Confidence Threshold**: If the translation engine's reported confidence score or an internally calculated confidence metric is **below 0.80**, you **MUST** append the disclaimer `[low-confidence translation]` to the end of the `translated` string in the output. This is non-negotiable and alerts downstream nodes to potential inaccuracies.
- **Token & Length Limits**: Adhere strictly to the context window limits of the underlying translation tools. For large texts, the Planner must split the content upstream before invoking this skill. Do not assume the skill handles chunking automatically.
- **Hallucination Prevention**: This skill must translate the provided text only. It must NOT add explanatory notes, summaries, or commentary not present in the source. Its role is transduction, not interpretation or expansion.
- **Scope Limitation**: Operates solely on the text payload provided. It must NOT fetch additional context from the web or previous agent states to inform the translation unless such context is explicitly passed in the input.
- **Idiom & Culture Handling**: Acknowledge that some phrases may not translate directly. The skill should aim for the most semantically equivalent common phrase in the target language, not a literal, nonsensical translation.
- **Format Preservation**: Make a best-effort attempt to preserve basic formatting like paragraph breaks, list markers, and punctuation. However, complex markup (HTML, Markdown) may not be perfectly retained and should be handled by a dedicated formatting skill if required.
- **Fallback Protocol**: If the primary LibreTranslate service is unavailable or does not support the language pair, automatically switch to the configured Google Translate fallback. Do not fail the skill without attempting the fallback.