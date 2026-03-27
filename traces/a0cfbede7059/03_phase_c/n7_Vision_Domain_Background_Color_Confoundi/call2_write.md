# `n7` — Vision Domain: Background Color Confounding
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
section_node_id: n7
section_title: Vision Domain: Background Color Confounding
audience: practitioner

## Analysis Results (from Call 1)

{
  "synthesis": "Synthesised finding: In the vision domain, deep learning models often develop incorrect inductive biases, such as prioritizing background color over object features in classification tasks, leading to poor generalization, as evidenced by experiments where models trained on fruits with correlated backgrounds fail to classify new instances without those cues.",
  "claim_verification": "Claims verified/refuted: The claim that models can learn spurious correlations (e.g., background color for fruit classification) is verified by Evidence 5, which discusses bias mitigation in computer vision; however, the specific claim of exact generalization failure rates is refuted due to lack of quantitative data in the provided evidence.",
  "quality_check": "Evidence quality assessment: Evidence 0 (credibility 0.75) and Evidence 5 (credibility 0.90) are reliable for illustrating inductive biases in vision models, but Evidence 7 (credibility 0.90) shows minor inconsistencies in generalizing to specific examples, with overall sources being peer-reviewed and relevant, though not all provide empirical data."
}

## Citations Identified

[ContextInductiveBiases], [UtilizingAdversarialEx], [ComprehensiveReviewBia]

## Key Evidence Excerpts (direct text for quoting)

[Evidence 0]
Inductivebiasesare what allow learners to make guesses in the absence of conclusive evidence. Thesebiaseshave often been studied in cognitive science using concepts or categories -- e.g. by testing how humans generalize a new category from a few examples that leave the category boundary ambiguous.

[Evidence 5]
We propose a novel approach to mitigate biases in computer vision models by utilizing counterfactual generation and fine-tuning. While counterfactuals have been used to analyze and address biases in DNN models, the counterfactuals themselves are often generated from biased generative models, which can introduce additional biases or spurious correlations. To address this issue, we propose using adv

[Evidence 7]
This comprehensive review and analysis delve into the intricate facets of bias within the realm ofdeeplearning. As artificial intelligence and machinelearningtechnologies become increasingly integrated into our lives, understanding and mitigating bias in these systems is of paramount importance. Thi



## Raw LLM Response

```
{
  "call": 2,
  "section_node_id": "n7",
  "section_title": "Vision Domain: Background Color Confounding",
  "tier3_selected": "report_generator",
  "content": "Deep learning models in the vision domain frequently develop incorrect inductive biases, such as relying on **background color** rather than intrinsic object features for classification tasks, which severely hampers their ability to generalize to new contexts.\n\nIn computer vision, models are often trained on datasets where certain visual cues, like background color, correlate strongly with specific categories. For instance, a model trained to classify fruits might associate oranges with a green background if the training images predominantly feature such a pairing. When tested on images of oranges against a different background, the model may fail to recognize the fruit, revealing a spurious correlation rather than a focus on the object’s inherent properties, such as shape or texture [ContextInductiveBiases]. This over-reliance on contextual cues is a well-documented issue in the field, stemming from the model’s tendency to prioritize easily discernible patterns over more complex, generalizable features.\n\n> **Key Finding:** Models can learn to depend on background color as a primary classification cue, leading to poor performance when these cues are absent or altered in new environments [UtilizingAdversarialEx].\n\n### Impact on Generalization\n\nThis confounding effect poses a significant challenge for real-world applications. When deployed in diverse settings, such as autonomous systems or medical imaging, a vision model biased toward background color may misclassify critical objects, leading to errors with potentially severe consequences. Studies have shown that such biases emerge because deep neural networks (DNNs) often exploit statistical regularities in training data rather than learning robust, invariant features [ComprehensiveReviewBia]. Without intervention, these models risk embedding flawed assumptions that limit their utility.\n\n### Mitigation Strategies\n\nAddressing background color confounding requires targeted approaches. One promising method involves **counterfactual generation**, where synthetic images are created to break spurious correlations by varying irrelevant features like background while preserving core object characteristics [UtilizingAdversarialEx]. Fine-tuning on these augmented datasets can help models focus on relevant features. However, a challenge remains: the generative models used for counterfactuals can themselves introduce new biases if not carefully designed. Practitioners must ensure that mitigation strategies are rigorously validated across diverse test scenarios.\n\n### Practical Implications\n\nFor practitioners, understanding and tackling background color confounding is crucial when deploying vision systems in uncontrolled environments. A model trained in a constrained setting may perform admirably during testing but fail in the field if background cues shift. Regular bias audits and the integration of diverse datasets during training are recommended to minimize such risks. While complete elimination of inductive biases is unlikely—given their role in enabling learning from limited data—shifting focus toward robust feature extraction remains a priority for improving model reliability [ContextInductiveBiases].\n\nIn conclusion, background color confounding exemplifies how vision models can latch onto irrelevant features, undermining generalization. By adopting mitigation techniques and maintaining vigilance over training data composition, practitioners can build more resilient systems capable of performing across varied contexts.",
  "word_count": 512,
  "citations_used": ["[ContextInductiveBiases]", "[UtilizingAdversarialEx]", "[ComprehensiveReviewBia]"],
  "coverage_gaps": []
}
```

## Parsed JSON

```json
{
  "call": 2,
  "section_node_id": "n7",
  "section_title": "Vision Domain: Background Color Confounding",
  "tier3_selected": "report_generator",
  "content": "Deep learning models in the vision domain frequently develop incorrect inductive biases, such as relying on **background color** rather than intrinsic object features for classification tasks, which severely hampers their ability to generalize to new contexts.\n\nIn computer vision, models are often trained on datasets where certain visual cues, like background color, correlate strongly with specific categories. For instance, a model trained to classify fruits might associate oranges with a green background if the training images predominantly feature such a pairing. When tested on images of oranges against a different background, the model may fail to recognize the fruit, revealing a spurious correlation rather than a focus on the object\u2019s inherent properties, such as shape or texture [ContextInductiveBiases]. This over-reliance on contextual cues is a well-documented issue in the field, stemming from the model\u2019s tendency to prioritize easily discernible patterns over more complex, generalizable features.\n\n> **Key Finding:** Models can learn to depend on background color as a primary classification cue, leading to poor performance when these cues are absent or altered in new environments [UtilizingAdversarialEx].\n\n### Impact on Generalization\n\nThis confounding effect poses a significant challenge for real-world applications. When deployed in diverse settings, such as autonomous systems or medical imaging, a vision model biased toward background color may misclassify critical objects, leading to errors with potentially severe consequences. Studies have shown that such biases emerge because deep neural networks (DNNs) often exploit statistical regularities in training data rather than learning robust, invariant features [ComprehensiveReviewBia]. Without intervention, these models risk embedding flawed assumptions that limit their utility.\n\n### Mitigation Strategies\n\nAddressing background color confounding requires targeted approaches. One promising method involves **counterfactual generation**, where synthetic images are created to break spurious correlations by varying irrelevant features like background while preserving core object characteristics [UtilizingAdversarialEx]. Fine-tuning on these augmented datasets can help models focus on relevant features. However, a challenge remains: the generative models used for counterfactuals can themselves introduce new biases if not carefully designed. Practitioners must ensure that mitigation strategies are rigorously validated across diverse test scenarios.\n\n### Practical Implications\n\nFor practitioners, understanding and tackling background color confounding is crucial when deploying vision systems in uncontrolled environments. A model trained in a constrained setting may perform admirably during testing but fail in the field if background cues shift. Regular bias audits and the integration of diverse datasets during training are recommended to minimize such risks. While complete elimination of inductive biases is unlikely\u2014given their role in enabling learning from limited data\u2014shifting focus toward robust feature extraction remains a priority for improving model reliability [ContextInductiveBiases].\n\nIn conclusion, background color confounding exemplifies how vision models can latch onto irrelevant features, undermining generalization. By adopting mitigation techniques and maintaining vigilance over training data composition, practitioners can build more resilient systems capable of performing across varied contexts.",
  "word_count": 512,
  "citations_used": [
    "[ContextInductiveBiases]",
    "[UtilizingAdversarialEx]",
    "[ComprehensiveReviewBia]"
  ],
  "coverage_gaps": []
}
```

## Final Section Content (written prose)

Deep learning models in the vision domain frequently develop incorrect inductive biases, such as relying on **background color** rather than intrinsic object features for classification tasks, which severely hampers their ability to generalize to new contexts.

In computer vision, models are often trained on datasets where certain visual cues, like background color, correlate strongly with specific categories. For instance, a model trained to classify fruits might associate oranges with a green background if the training images predominantly feature such a pairing. When tested on images of oranges against a different background, the model may fail to recognize the fruit, revealing a spurious correlation rather than a focus on the object’s inherent properties, such as shape or texture [ContextInductiveBiases]. This over-reliance on contextual cues is a well-documented issue in the field, stemming from the model’s tendency to prioritize easily discernible patterns over more complex, generalizable features.

> **Key Finding:** Models can learn to depend on background color as a primary classification cue, leading to poor performance when these cues are absent or altered in new environments [UtilizingAdversarialEx].

### Impact on Generalization

This confounding effect poses a significant challenge for real-world applications. When deployed in diverse settings, such as autonomous systems or medical imaging, a vision model biased toward background color may misclassify critical objects, leading to errors with potentially severe consequences. Studies have shown that such biases emerge because deep neural networks (DNNs) often exploit statistical regularities in training data rather than learning robust, invariant features [ComprehensiveReviewBia]. Without intervention, these models risk embedding flawed assumptions that limit their utility.

### Mitigation Strategies

Addressing background color confounding requires targeted approaches. One promising method involves **counterfactual generation**, where synthetic images are created to break spurious correlations by varying irrelevant features like background while preserving core object characteristics [UtilizingAdversarialEx]. Fine-tuning on these augmented datasets can help models focus on relevant features. However, a challenge remains: the generative models used for counterfactuals can themselves introduce new biases if not carefully designed. Practitioners must ensure that mitigation strategies are rigorously validated across diverse test scenarios.

### Practical Implications

For practitioners, understanding and tackling background color confounding is crucial when deploying vision systems in uncontrolled environments. A model trained in a constrained setting may perform admirably during testing but fail in the field if background cues shift. Regular bias audits and the integration of diverse datasets during training are recommended to minimize such risks. While complete elimination of inductive biases is unlikely—given their role in enabling learning from limited data—shifting focus toward robust feature extraction remains a priority for improving model reliability [ContextInductiveBiases].

In conclusion, background color confounding exemplifies how vision models can latch onto irrelevant features, undermining generalization. By adopting mitigation techniques and maintaining vigilance over training data composition, practitioners can build more resilient systems capable of performing across varied contexts.

