# explainer

**Tier**: output  
**Name**: `explainer`  

## Description

The `explainer` skill is a specialized output generation module designed to transform complex, technical, or domain-specific information into an accessible, engaging, and educational narrative for non-expert audiences. It performs a sophisticated cognitive and linguistic transformation process, which involves:

1.  **Input Analysis & Deconstruction**: The skill first parses the provided input data (typically structured notes, research summaries, or technical descriptions) to identify core concepts, key terminology, and logical relationships between ideas.
2.  **Jargon Neutralization**: It actively scans for specialized jargon, acronyms, and technical terms. Upon the first instance of each term, it provides an immediate, plain-language definition enclosed in parentheses (e.g., "The algorithm uses a heuristic (a practical shortcut or rule-of-thumb) to find a solution."). This ensures comprehension is built incrementally without requiring prior knowledge.
3.  **Conceptual Mapping & Analogy Generation**: For each major, abstract, or difficult concept identified, the skill constructs a relatable, concrete analogy drawn from everyday life, common experiences, or widely understood domains. This bridges the gap between unfamiliar technical territory and the user's existing mental models.
4.  **Narrative Structuring**: It organizes the explanation into a logical flow, often using a "funnel" structure: starting with a high-level "big picture" hook, breaking down the component parts, and then synthesizing how they work together. It employs transitional phrases, clear topic sentences, and a consistent, friendly tone.
5.  **Linguistic Calibration**: The final text is rigorously adjusted to meet a target reading level, utilizing simpler sentence structures, active voice, and common vocabulary while preserving factual accuracy and conceptual integrity. The output is not a simplified summary but a pedagogically reconstructed explanation.

The physical output is a coherent, standalone document that can be understood without reference to the original, technical source material.

## When to Use

Use this skill as the final or near-final node in an execution DAG when the primary goal is user education, public communication, or foundational understanding.

*   **Specific Scenarios**:
    *   The `audience` parameter in the plan is explicitly set to `'layperson'`, `'general public'`, `'student'`, or `'non-technical stakeholder'`.
    *   The `output_format` in the plan is specified as `'explainer'`, `'plain_language_summary'`, or `'educational_overview'`.
    *   The upstream data is inherently complex (e.g., scientific paper summaries, financial analysis, software architecture diagrams, legal clause breakdowns) and requires translation.
    *   The task is to create content for public-facing blogs, instructional materials, internal onboarding documents, or stakeholder presentations where clarity is paramount.
*   **Upstream Dependencies & Expected Input**:
    *   This skill **requires high-quality, accurate, and structured input**. It is not a research tool.
    *   **Ideal Input**: The output from a `researcher`, `analyst`, or `summarizer` skill—such as consolidated notes, a fact-checked summary, or a well-structured concept breakdown. The input should be in clear text format, containing the core information to be explained.
    *   **Poor Input**: Raw, unprocessed data tables, unstructured web snippets, or highly opinionated/unsourced content. The skill will attempt to explain whatever it is given, so garbage in leads to a misleading explanation out.
*   **Edge Cases - When NOT to Use**:
    *   **For Technical Audiences**: If the audience is `'expert'`, `'developer'`, or `'academic'`, use a `reporter`, `analyst`, or `critic` skill instead.
    *   **For Persuasive or Argumentative Output**: If the goal is to argue a point, critique a work, or persuade, use the `critic` or `advocate` skill. The explainer is neutral and educational.
    *   **For Creative or Narrative Storytelling**: If the goal is to generate a story, marketing copy, or creative narrative, use the `storyteller` or `copywriter` skill.
    *   **As a Substitute for Research**: Do not use this skill to generate new facts or insights. It only reformats and explains provided information.
*   **Downstream Nodes**:
    *   Typically, this is a terminal output node. Its output (`OutputDocument`) can be passed directly to a `formatter` or `deliverable` skill for final presentation (e.g., PDF generation, web page formatting).
    *   It is rarely followed by another analytical skill, as its purpose is to conclude an analytical chain with communication.

## Execution Model

LLM-based

**Prompt file**: `prompts/explainer.md`

## Output Contract

OutputDocument — explainer text with plain-language glossary, analogies

## Constraints

*   **Jargon Handling Mandate**: **Every** instance of technical jargon, domain-specific terminology, or non-common acronyms **must** be followed by a plain-language definition in parentheses on its **first use** in the document. This is non-negotiable for accessibility.
*   **Analogy Quota**: Generate **at least one** clear, concrete, and relatable analogy for every major conceptual pillar of the explanation. Avoid overusing analogies for minor points. The analogies must be accurate and not misleading.
*   **Reading Level Enforcement**:
    *   For a general `'layperson'` audience, strictly target a **~8th-grade (US) reading level**. Use short sentences, common words, and clear cause-and-effect structures.
    *   For a `'student'` or `'high-school'` audience, you may target a **~12th-grade level**, allowing for slightly more complex sentence structures and a broader, but still common, vocabulary.
    *   The LLM must actively self-check against these targets.
*   **Hallucination Prohibition**: The explanation **must only** rephrase and elucidate the concepts present in the provided input data. Do not introduce new facts, examples, or data points not contained in or directly implied by the source input. If the input is incomplete, note the gap plainly; do not invent to fill it.
*   **Tone & Scope**: Maintain a helpful, patient, and encouraging tone. Avoid condescension. The scope is strictly limited to explaining the provided input; do not add disclaimers, editorial commentary, or unrelated background information unless it is critically necessary for basic understanding and can be inferred from the input.
*   **Output Structure**: The output must be a fluent, continuous piece of prose suitable for reading. It should not be a bulleted list of term definitions but a cohesive narrative that integrates definitions and analogies naturally.