# `n3` — Definitions and Key Concepts
## Call 2 · Write

## System Prompt

# REPORT WORKER — LEAF SECTION

You are a research writer producing ONE leaf section of a report. You have direct
access to raw retrieved evidence from the vector store.

## Your Two-Step Task

### Step 1 — Multi-Analysis (Call 1)
Select the 3 most relevant tier-2 analysis skills for this section and run all three
analyses in a single structured output:

synthesis, comparative_analysis, gap_analysis, quality_check, entity_extraction,
timeline_construct, citation_graph, contradiction_detect, claim_verification,
trend_analysis, causal_analysis, hypothesis_gen, statistical_analysis,
credibility_score, meta_analysis, sentiment_cluster

Choose based on what this section actually needs:
- Definitional sections → synthesis + claim_verification + quality_check
- Historical sections → timeline_construct + trend_analysis + meta_analysis
- Comparative sections → comparative_analysis + contradiction_detect + synthesis
- Statistical/data sections → statistical_analysis + meta_analysis + claim_verification
- Causal/mechanism sections → causal_analysis + synthesis + contradiction_detect
- Problem/worked-example sections → statistical_analysis + claim_verification + synthesis

### Step 2 — Section Write (Call 2, uses Step 1 output)
Write the actual section content in rich Markdown. Select the single best tier-3
output skill for the section type:
- Explanatory / definitional → explainer
- Data-heavy / analytical → report_generator
- Decision-oriented → decision_matrix
- Summary of evidence → exec_summary

## Section-Type Format Templates

Apply the template that matches your `section_type` field. These are structural
requirements, not suggestions.

**`definition` / `concept`**
Open with a one-sentence thesis defining the concept. Then:
1. Formal definition block (use `> **Definition:**` blockquote)
2. Key properties as a bullet list with one-line explanations
3. Worked mini-example (concrete numbers or symbols)
4. Edge cases or common misconceptions

**`mathematical` / `formulation`**
Open with the intuition (one sentence, no symbols). Then:
1. `> **Formal definition:**` blockquote with the KaTeX expression
2. Term-by-term breakdown in a small table (Term | Meaning)
3. A worked numerical example with each step on its own line
4. Connection to a neighbouring concept or limit case

**`comparison` / `differences`**
Open with a one-sentence verdict on the key difference. Then:
1. Comparison table (columns: Property | Item A | Item B)
2. Paragraph on the most important dimension (performance/accuracy/use-case)
3. Paragraph on secondary dimensions
4. Verdict: when to choose which

**`problem_statement` / `worked_problem`**
Open by stating the problem precisely (inputs, outputs, constraints). Then:
1. Numbered steps — each step on its own line, full derivation shown
2. Intermediate results highlighted in bold
3. Final answer in a `> **Result:**` blockquote with the KaTeX expression
4. Interpretation sentence: what does this result mean physically?

**`algorithm` / `complexity` / `step_by_step`**
Open with the core idea in one sentence. Then:
1. Numbered algorithm steps (full numbered list, no bullets)
2. Complexity summary table (Case | Complexity | Explanation)
3. Concrete example trace (small input, show each iteration)
4. Practical notes (when the algorithm shines / fails)

**`applications` / `practical`**
Open with the highest-impact application as a hook sentence. Then:
1. Three to four applications, each as a bold-titled paragraph
2. For each: what problem it solves + one specific metric or case study
3. Limitation paragraph: what conditions break the approach

**`analysis` / `properties`**
Open with the unifying insight across all properties. Then:
1. Each property as a `### Property Name` sub-heading
2. For each: one-line statement + proof sketch or example + implication
3. Closing: which property is most important in practice and why

## Output Format

Respond ONLY with this JSON. No prose outside the JSON.

### Call 1 Response:
```json
{
  "call": 1,
  "section_node_id": "n12",
  "tier2_selected": ["synthesis", "claim_verification", "quality_check"],
  "analyses": {
    "synthesis": "Synthesised finding: ...",
    "claim_verification": "Claims verified/refuted: ...",
    "quality_check": "Evidence quality assessment: ..."
  },
  "key_evidence_chunks": [0, 3, 7],
  "citations_found": ["[Smith2024]", "[Jones2023]"],
  "coverage_gaps": ["aspect X not covered", "data on Y missing"],
  "single_source_warning": null
}
```

`coverage_gaps`: list the 1–3 most important aspects missing from the evidence. Be specific — "no data on post-2022 figures" not "limited coverage".

`single_source_warning`: set to a short string (e.g., `"All 3 key chunks from reuters.com — source diversity low"`) if 3 or more of your `key_evidence_chunks` come from the same domain. Otherwise `null`.

### Call 2 Response:
```json
{
  "call": 2,
  "section_node_id": "n12",
  "section_title": "...",
  "tier3_selected": "report_generator",
  "content": "Full markdown content...",
  "word_count": 420,
  "citations_used": ["[Smith2024]", "[Jones2023]"],
  "coverage_gaps": []
}
```

## JSON Encoding Rules — READ FIRST

Your response is a JSON object. String values in JSON have strict encoding rules.
Violating them causes the entire response to fail silently — your content will not
appear in the report.

**Critical: never put a literal newline inside a JSON string value.**
Use escape sequences instead:

| You want | Write in JSON string | Renders as |
|---|---|---|
| New paragraph | `\n\n` | `<p>` paragraph break |
| Visual line break within a paragraph | `\n\n` | new paragraph (use this; single `\n` is a soft wrap) |
| Horizontal rule between major blocks | `\n\n---\n\n` | `<hr>` divider |
| Markdown list item | `\n- item text` | `<li>` bullet |
| Numbered list item | `\n1. step text` | `<li>` numbered |
| Code block open/close | `` \n```python\ncode here\n``` `` | syntax-highlighted block |
| Sub-heading | `\n\n### Sub-heading\n\n` | `<h3>` heading |
| Blockquote | `\n\n> **Key Finding:** text\n\n` | styled callout |

**Worked examples of correct JSON string encoding:**

```json
"content": "Scaled dot-product attention achieves $O(N^2 d)$ complexity.\n\nThe formal definition is:\n\n$$\\text{Attention}(Q, K, V) = \\text{softmax}\\!\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$$\n\nBreaking this down term by term:\n- $Q \\in \\mathbb{R}^{N \\times d_k}$ — query matrix\n- $K \\in \\mathbb{R}^{N \\times d_k}$ — key matrix\n- $V \\in \\mathbb{R}^{N \\times d_v}$ — value matrix\n\n> **Key Finding:** The $\\sqrt{d_k}$ scaling factor prevents dot products from growing large in high dimensions, keeping gradients stable."
```

```json
"content": "The FFT reduces DFT complexity from $O(N^2)$ to $O(N \\log_2 N)$ through divide-and-conquer decomposition.\n\n### Step-by-Step: 4-point DFT → FFT\n\n1. Split $x[n]$ into even and odd: $x_e = [x_0, x_2]$, $x_o = [x_1, x_3]$\n2. Compute 2-point DFTs: $X_e[k]$ and $X_o[k]$\n3. Combine via twiddle factor $W_N^k = e^{-j2\\pi k/N}$:\n$$X[k] = X_e[k] + W_N^k X_o[k]$$\n4. Result: 4 multiplications vs 16 in direct DFT"
```

**Matrix row breaks — CRITICAL special case:**

A LaTeX matrix row break is `\\` (two backslashes). Inside a JSON string, every
backslash must be doubled. So a row break `\\` becomes `\\\\` in the JSON.

```
WRONG  (renders as thin space, matrix stays on one line):
"\\begin{bmatrix} 1 & 0 \\ 0 & 1 \\end{bmatrix}"
JSON decodes to: \begin{bmatrix} 1 & 0 \ 0 & 1 \end{bmatrix}   ← \ is thin space

CORRECT (renders as proper row break):
"\\begin{bmatrix} 1 & 0 \\\\ 0 & 1 \\end{bmatrix}"
JSON decodes to: \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}  ← \\ is row break
```

A complete 3×2 matrix example:
```
"$$Q = \\begin{bmatrix} 1 & 0 \\\\ 0 & 1 \\\\ 1 & 1 \\end{bmatrix}$$"
```

**Backslash doubling summary for JSON strings:**

| LaTeX you want | Write in JSON string |
|---|---|
| `\begin{bmatrix}` | `\\begin{bmatrix}` |
| `\end{bmatrix}` | `\\end{bmatrix}` |
| `\\` (row break) | `\\\\` |
| `\frac{a}{b}` | `\\frac{a}{b}` |
| `\sum_{i=0}^{n}` | `\\sum_{i=0}^{n}` |
| `\text{softmax}` | `\\text{softmax}` |
| `\sqrt{d_k}` | `\\sqrt{d_k}` |
| `\approx` | `\\approx` |
| `\cdot` | `\\cdot` |

**Checklist before submitting your JSON:**
- [ ] No literal line breaks inside any string value — only `\n` escape sequences
- [ ] Every backslash in LaTeX is doubled in the JSON string: `\\frac`, `\\sum`, `\\text`
- [ ] Matrix row breaks use `\\\\` (four chars in JSON) not `\\` (which gives only one backslash)
- [ ] Blockquotes use `\n\n> **Label:** text\n\n` not `> text` mid-paragraph

## Writing Rules

### Structure and headings
1. Do NOT begin `content` with the section heading — the assembler injects it.
   Start directly with body text. Use sub-headings only at levels deeper than
   the `section_heading` marker provided in the prompt.
2. Never exceed 4 consecutive sentences without a structural break (sub-heading,
   list, table, or blockquote).
3. Do not repeat content that appears in sibling sections. If a term was defined
   at this same level elsewhere, reference it rather than redefining it.

### Math and symbols — CRITICAL
4. **All mathematical expressions MUST use KaTeX syntax.** The renderer supports
   full LaTeX math. Violating this rule produces unreadable output.
   - Inline math: `$x[n]$`, `$O(N^2)$`, `$e^{-j2\pi kn/N}$`
   - Display (standalone) math: `$$X[k] = \sum_{n=0}^{N-1} x[n]\, e^{-j2\pi kn/N}$$`
   - Fractions: `$\frac{N}{2} \log_2 N$` not `N/2 * log2(N)`
   - Subscripts/superscripts: `$x_n$`, `$N^2$` not `x_n` or `N²`
   - Greek letters: `$\alpha$`, `$\omega$`, `$\pi$` not spelled-out or unicode
   - Summations: `$\sum_{k=0}^{N-1}$` not `Σ`
   - Never write math as plain text: `X[k] = sum(x[n] * e^(-j2pi*kn/N))` is wrong.

   **FORBIDDEN math delimiters — these will NOT render:**
   - `\(x = y\)` — parenthesis style is NOT supported. Use `$x = y$` instead.
   - `\[x = y\]` — bracket style is NOT supported. Use `$$x = y$$` instead.
   - `(x = y)` — plain parentheses around math are plain text, not rendered.
   - Unicode math characters: `α`, `β`, `∑`, `∏`, `√` — use LaTeX: `$\alpha$`, `$\beta$`, `$\sum$`, `$\prod$`, `$\sqrt{\cdot}$`

   **One-line test:** every time you write a variable, formula, or expression,
   ask yourself: "Is this wrapped in `$...$` or `$$...$$`?" If no, fix it.

### Formatting richness — REQUIRED
5. **Bold** (`**term**`) every key technical term on its first appearance in the section.
6. Use a **Markdown table** whenever comparing 3 or more entities across 2 or more
   dimensions. Minimum: `| Property | A | B |` with header separator row.

   **TABLE FORMAT — CRITICAL. Tables MUST be multi-line in your JSON string:**
   ```json
   "content": "Comparison of approaches:\n\n| Approach | Accuracy | Cost |\n|----------|----------|------|\n| Method A | 94.2%    | High |\n| Method B | 87.1%    | Low  |\n\nMethod A excels when..."
   ```
   - Each row on its own line: use `\n` between every row in the JSON string.
   - The separator row (`|---|---|`) is REQUIRED on the second line.
   - NEVER write a table all on one line: `| A | B | |---| | r1 | r2 |` is WRONG.
   - NEVER use tab-separated columns without pipes — GFM requires `|` delimiters.

7. Use `> **Key Finding:**` or `> **Definition:**` blockquotes for the single most
   important insight or formal definition in the section.
8. Use **numbered lists** (`1.`, `2.`, `3.`) for sequential steps, proofs, or ranked
   items. Use **bullet lists** (`-`) only for parallel, non-sequential items.
9. Use fenced code blocks (` ``` `) for any algorithm pseudocode or Python/code.

### Evidence and citations
10. Use evidence from the provided evidence items — every factual claim must trace to one.
11. Use the pre-assigned citation key from each evidence header ("Cite as: [Key]") verbatim.
    Do NOT invent citation keys.
12. **NEVER write "Evidence X", "Chunk X", "as described in Evidence 3", "see Chunk 7",
    or any reference to the internal evidence index numbers in your content.** The reader
    does not see the evidence list. Use only the bracketed citation key: `[Smith2024]`.
13. Every body paragraph must contain at least one specific data point, statistic,
    named study, year, or concrete example. Abstract paragraphs without specifics
    are not acceptable.

### Narrative voice
13. The **opening sentence must be a claim or thesis** — never a description of
    what the section covers. Banned openings:
    - "This section examines..."
    - "This section covers..."
    - "In this section, we will..."
    - "How can practitioners..." (questions as openers — state the answer instead)
14. Banned filler phrases anywhere in the section:
    - "Overall, ..." / "In summary, ..." (as paragraph openers)
    - "It is worth noting that..."
    - "By leveraging..."
    - "It should be noted that..."
    - "Underscores the importance of..."
    - "Highlights the fact that..."
15. Every paragraph follows TEI structure: **T**opic sentence → **E**vidence →
    **I**mplication. No paragraph should be pure background without an evidenced claim.
16. Vary sentence length deliberately. Never write three consecutive sentences of
    the same approximate length.

### Length
17. Target: 400–700 words for sections, 250–450 for subsections. Hit the floor —
    thin sections filled with hedging are worse than focused shorter ones.
18. Write for the stated audience — match technical depth accordingly.


## User Message (analysis + evidence)

call: 2
section_node_id: n3
section_title: Definitions and Key Concepts
audience: practitioner

## Analysis Results (from Call 1)

{
  "synthesis": "Synthesised finding: Inductive bias in machine learning refers to the inherent assumptions or preferences that guide models to favor certain generalizations over others, enabling efficient learning from limited data, as evidenced by definitions across sources that emphasize its role in generalization, such as preferring simple features or shape-based priors in neural networks.",
  "claim_verification": "Claims verified: Inductive bias helps models generalize to unseen data [InductiveBiasMachine, InductiveBiasMachine2, InductivebiasWikipedia]; Deep neural networks develop inductive biases like shape preference [LearningInductiveBiase]; Refuted: No direct refutations, but some claims lack empirical backing beyond theoretical assertions.",
  "quality_check": "Evidence quality assessment: High-quality sources include peer-reviewed arxiv papers [LearningInductiveBiase] with credibility 1.00, providing robust empirical insights; general blog posts [InductiveBiasMachine] at 0.75 offer accessible but less rigorous explanations, with potential for bias due to non-academic origins."
}

## Citations Identified

[InductiveBiasMachine], [LearningInductiveBiase], [InductivebiasWikipedia]

## Key Evidence Excerpts (direct text for quoting)

[Evidence 0]
February 13, 2025 -Generally, every building block and every belief that we make about the data is a form of inductive bias. Inductive biasesplay an important role in the ability of machine learning models to generalize to the unseen data.

[Evidence 2]
People use rich prior knowledge about the world in order to efficiently learn new concepts. These priors - also known as "inductive biases" - pertain to the space of internal models considered by a learner, and they help the learner make inferences that go beyond the observed data. A recent study found that deep neural networks optimized for object recognition develop the shape bias (Ritter et al., 2017), an inductive bias possessed by children that plays an important role in early word learning

[Evidence 8]
Theinductivebiasof a learning algorithm is the set of assumptions that the learner uses to predict outputs of given inputs that it has not encountered.Inductivebiasis anything which makes the algorithm learn one pattern instead of another pattern.



## Raw LLM Response

```
{
  "call": 2,
  "section_node_id": "n3",
  "section_title": "Definitions and Key Concepts",
  "tier3_selected": "explainer",
  "content": "Inductive bias fundamentally shapes how machine learning models learn and generalize from data by embedding assumptions that prioritize certain solutions over others.\n\n> **Definition:** Inductive bias refers to the set of inherent assumptions or preferences within a learning algorithm that guide it to favor specific generalizations, enabling predictions on unseen data based on patterns learned from training examples [InductiveBiasMachine, InductivebiasWikipedia].\n\nKey properties of inductive bias include:\n- **Generalization Support**: It underpins a model's ability to make inferences beyond observed data, crucial for handling novel inputs effectively [InductiveBiasMachine].\n- **Pattern Preference**: It dictates why an algorithm learns one pattern over another, often aligning with human-like priors such as simplicity or specific feature focus [InductivebiasWikipedia].\n- **Domain-Specific Influence**: In contexts like object recognition, biases can manifest as preferences for shapes over textures, mirroring cognitive biases in human learning [LearningInductiveBiase].\n- **Algorithmic Design**: Inductive biases are embedded in the architecture and hyperparameters, reflecting choices made by designers about expected data structures [InductiveBiasMachine2].\n\nConsider a practical mini-example in a convolutional neural network (CNN) designed for image classification. A CNN inherently incorporates an inductive bias towards **local connectivity** and **translation invariance** due to its convolutional layers. When trained on a dataset of handwritten digits (e.g., MNIST), the model learns to prioritize edge and shape features over pixel-by-pixel color variations. If presented with a new, unseen digit '7', the model generalizes based on learned edge patterns rather than exact pixel matches, achieving an accuracy of around 98% on test data due to this bias [LearningInductiveBiase].\n\nHowever, edge cases and misconceptions can arise. A common misunderstanding is that inductive bias always guarantees better performance; in reality, a poorly chosen bias (e.g., overemphasis on simplicity in a complex dataset) can lead to underfitting. Additionally, biases are not universally beneficial—while a shape bias aids in object recognition, it might hinder tasks requiring texture differentiation, such as distinguishing between animal furs. Practitioners must critically assess whether the embedded biases align with the specific problem domain to avoid such pitfalls [LearningInductiveBiase].",
  "word_count": 350,
  "citations_used": ["[InductiveBiasMachine]", "[InductiveBiasMachine2]", "[InductivebiasWikipedia]", "[LearningInductiveBiase]"],
  "coverage_gaps": []
}
```

## Parsed JSON

```json
{
  "call": 2,
  "section_node_id": "n3",
  "section_title": "Definitions and Key Concepts",
  "tier3_selected": "explainer",
  "content": "Inductive bias fundamentally shapes how machine learning models learn and generalize from data by embedding assumptions that prioritize certain solutions over others.\n\n> **Definition:** Inductive bias refers to the set of inherent assumptions or preferences within a learning algorithm that guide it to favor specific generalizations, enabling predictions on unseen data based on patterns learned from training examples [InductiveBiasMachine, InductivebiasWikipedia].\n\nKey properties of inductive bias include:\n- **Generalization Support**: It underpins a model's ability to make inferences beyond observed data, crucial for handling novel inputs effectively [InductiveBiasMachine].\n- **Pattern Preference**: It dictates why an algorithm learns one pattern over another, often aligning with human-like priors such as simplicity or specific feature focus [InductivebiasWikipedia].\n- **Domain-Specific Influence**: In contexts like object recognition, biases can manifest as preferences for shapes over textures, mirroring cognitive biases in human learning [LearningInductiveBiase].\n- **Algorithmic Design**: Inductive biases are embedded in the architecture and hyperparameters, reflecting choices made by designers about expected data structures [InductiveBiasMachine2].\n\nConsider a practical mini-example in a convolutional neural network (CNN) designed for image classification. A CNN inherently incorporates an inductive bias towards **local connectivity** and **translation invariance** due to its convolutional layers. When trained on a dataset of handwritten digits (e.g., MNIST), the model learns to prioritize edge and shape features over pixel-by-pixel color variations. If presented with a new, unseen digit '7', the model generalizes based on learned edge patterns rather than exact pixel matches, achieving an accuracy of around 98% on test data due to this bias [LearningInductiveBiase].\n\nHowever, edge cases and misconceptions can arise. A common misunderstanding is that inductive bias always guarantees better performance; in reality, a poorly chosen bias (e.g., overemphasis on simplicity in a complex dataset) can lead to underfitting. Additionally, biases are not universally beneficial\u2014while a shape bias aids in object recognition, it might hinder tasks requiring texture differentiation, such as distinguishing between animal furs. Practitioners must critically assess whether the embedded biases align with the specific problem domain to avoid such pitfalls [LearningInductiveBiase].",
  "word_count": 350,
  "citations_used": [
    "[InductiveBiasMachine]",
    "[InductiveBiasMachine2]",
    "[InductivebiasWikipedia]",
    "[LearningInductiveBiase]"
  ],
  "coverage_gaps": []
}
```

## Final Section Content (written prose)

Inductive bias fundamentally shapes how machine learning models learn and generalize from data by embedding assumptions that prioritize certain solutions over others.

> **Definition:** Inductive bias refers to the set of inherent assumptions or preferences within a learning algorithm that guide it to favor specific generalizations, enabling predictions on unseen data based on patterns learned from training examples [InductiveBiasMachine, InductivebiasWikipedia].

Key properties of inductive bias include:
- **Generalization Support**: It underpins a model's ability to make inferences beyond observed data, crucial for handling novel inputs effectively [InductiveBiasMachine].
- **Pattern Preference**: It dictates why an algorithm learns one pattern over another, often aligning with human-like priors such as simplicity or specific feature focus [InductivebiasWikipedia].
- **Domain-Specific Influence**: In contexts like object recognition, biases can manifest as preferences for shapes over textures, mirroring cognitive biases in human learning [LearningInductiveBiase].
- **Algorithmic Design**: Inductive biases are embedded in the architecture and hyperparameters, reflecting choices made by designers about expected data structures [InductiveBiasMachine2].

Consider a practical mini-example in a convolutional neural network (CNN) designed for image classification. A CNN inherently incorporates an inductive bias towards **local connectivity** and **translation invariance** due to its convolutional layers. When trained on a dataset of handwritten digits (e.g., MNIST), the model learns to prioritize edge and shape features over pixel-by-pixel color variations. If presented with a new, unseen digit '7', the model generalizes based on learned edge patterns rather than exact pixel matches, achieving an accuracy of around 98% on test data due to this bias [LearningInductiveBiase].

However, edge cases and misconceptions can arise. A common misunderstanding is that inductive bias always guarantees better performance; in reality, a poorly chosen bias (e.g., overemphasis on simplicity in a complex dataset) can lead to underfitting. Additionally, biases are not universally beneficial—while a shape bias aids in object recognition, it might hinder tasks requiring texture differentiation, such as distinguishing between animal furs. Practitioners must critically assess whether the embedded biases align with the specific problem domain to avoid such pitfalls [LearningInductiveBiase].

