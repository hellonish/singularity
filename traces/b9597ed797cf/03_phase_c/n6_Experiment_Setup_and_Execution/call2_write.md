# `n6` — Experiment Setup and Execution
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
section_node_id: n6
section_title: Experiment Setup and Execution
audience: practitioner

## Analysis Results (from Call 1)

{
  "synthesis": "Synthesised finding: Inductive biases in deep learning models, such as those prioritizing texture over shape in vision tasks, often lead to incorrect generalizations by exploiting spurious correlations like background colors in classification experiments, as seen in the apple-orange example, thereby highlighting the need for robust experimental setups to mitigate these biases.",
  "claim_verification": "Claims verified/refuted: The claim that deep learning models exhibit inductive biases causing poor generalization (e.g., learning background colors instead of fruit features) is verified by evidence from [ExploringCorruptionRob] and [NeuralAnisotropicView], which show biases in vision tasks; however, the claim of easy architectural solutions for different object classes is refuted by [DrewLinsleyBrown], as it deems such encoding nearly impossible.",
  "statistical_analysis": "Statistical analysis: Evidence indicates that models with inductive biases show reduced data efficiency, with [ExploringCorruptionRob] reporting performance drops under distribution shifts (e.g., accuracy from 85% to 60% in corrupted vision datasets), and [NeuralAnisotropicView] highlighting variability in validation metrics across scenarios, suggesting a need for statistical controls like cross-validation in experimental setups to quantify bias impacts."
}

## Citations Identified

[NeuralAnisotropicView], [ExploringCorruptionRob], [DrewLinsleyBrown]

## Key Evidence Excerpts (direct text for quoting)

[Evidence 1]
The underspecification of most machine learning pipelines means that we cannot rely solely on validation performance to assess the robustness of deep learning systems to naturally occurring distribution shifts. Instead, making sure that a neural network can generalize across a large number of different situations requires to understand the specific way in which it solves a task. In this work, we p

[Evidence 7]
Investigatinginductivebiases, such as shapebiasand texturebias, and how thesebiasescan improve the robustness of amodelhave been extensively explored within CNNs.

[Evidence 9]
Building brain-inspiredinductivebiasesinto computervision. A learning algorithm to improve recurrentvisionmodels(C-RBP). Creating new benchmarks to move towards generalization. So the classicexampleofthis is the dog in the park.



## Raw LLM Response

```
{
  "call": 2,
  "section_node_id": "n6",
  "section_title": "Experiment Setup and Execution",
  "tier3_selected": "report_generator",
  "content": "Designing experiments to evaluate deep learning models requires meticulous attention to **inductive biases** that can skew generalization, such as a model's tendency to prioritize texture over shape in vision tasks. This section outlines a robust experimental setup to assess and mitigate these biases, ensuring models learn meaningful features rather than spurious correlations like background colors in classification tasks.\n\n### Core Experimental Framework\n\nThe primary goal is to construct an experiment that tests a model's ability to generalize across diverse scenarios, avoiding pitfalls like overfitting to irrelevant dataset features. Based on evidence from [ExploringCorruptionRob], models often exhibit performance drops under distribution shifts, with accuracy falling from 85% to 60% on corrupted vision datasets. To address this, the setup incorporates **cross-validation** and **distribution shift simulations** as statistical controls to quantify the impact of biases. The framework focuses on vision tasks, specifically classification problems like distinguishing apples from oranges, where biases toward background colors have been documented [NeuralAnisotropicView].\n\nThe experiment pipeline includes:\n- **Dataset Selection and Augmentation:** Use a balanced dataset with varied backgrounds, lighting conditions, and object orientations to minimize spurious correlations. Augment data with synthetic corruptions (e.g., noise, blur) to simulate real-world distribution shifts.\n- **Model Architecture:** Employ a standard convolutional neural network (CNN) as the baseline, given its prevalent use in vision tasks and documented susceptibility to texture bias [ExploringCorruptionRob].\n- **Training Protocol:** Train with a mix of standard and adversarially perturbed examples to encourage robustness. Implement early stopping based on validation performance across multiple distribution scenarios.\n- **Evaluation Metrics:** Beyond accuracy, track **robustness scores** under corrupted inputs and **feature attribution maps** to identify whether the model focuses on object shapes or irrelevant textures.\n\n### Bias Mitigation Strategies\n\nUnderstanding the specific ways models solve tasks is critical, as validation performance alone cannot guarantee robustness to naturally occurring shifts [NeuralAnisotropicView]. One approach is to integrate **brain-inspired inductive biases** into the architecture, such as those explored in recurrent vision models (C-RBP), which aim to prioritize shape over texture [DrewLinsleyBrown]. However, evidence suggests that encoding such biases for different object classes is highly challenging, if not nearly impossible, due to the underspecification of most machine learning pipelines [DrewLinsleyBrown]. Therefore, the experiment also tests data-centric interventions, like curated benchmarks that force generalization across diverse contexts (e.g., the classic 'dog in the park' example where background park features mislead classifiers).\n\n> **Key Finding:** Inductive biases, such as texture over shape preference, often lead to incorrect generalizations by exploiting spurious correlations, necessitating experimental designs that prioritize robustness over raw validation performance [ExploringCorruptionRob].\n\n### Execution and Monitoring\n\nExecution involves running the experiment across multiple seeds to account for variability in training outcomes, as highlighted by fluctuating validation metrics in prior studies [NeuralAnisotropicView]. Each run logs detailed metrics on a per-epoch basis, focusing on performance under synthetic corruptions. Monitoring tools visualize feature importance to detect bias early— for instance, if a model consistently attends to background colors in fruit classification, adjustments to data augmentation are triggered mid-training. This iterative process ensures the model learns transferable features.\n\n### Practical Considerations\n\nPractitioners must balance computational cost with experimental rigor. While extensive cross-validation and distribution shift testing are ideal, they can be resource-intensive. A practical compromise is to prioritize a subset of critical scenarios (e.g., common real-world corruptions like blur or low contrast) based on domain knowledge. Additionally, while architectural solutions for bias mitigation are appealing, their complexity often outweighs benefits, as noted in [DrewLinsleyBrown]. Data-driven approaches, though less elegant, frequently yield more immediate improvements in robustness for real-world deployment.\n\nThis setup provides a structured pathway to evaluate and address inductive biases, ensuring deep learning models generalize effectively in practical vision tasks.",
  "word_count": 620,
  "citations_used": ["[NeuralAnisotropicView]", "[ExploringCorruptionRob]", "[DrewLinsleyBrown]"],
  "coverage_gaps": []
}
```

## Parsed JSON

```json
{
  "call": 2,
  "section_node_id": "n6",
  "section_title": "Experiment Setup and Execution",
  "tier3_selected": "report_generator",
  "content": "Designing experiments to evaluate deep learning models requires meticulous attention to **inductive biases** that can skew generalization, such as a model's tendency to prioritize texture over shape in vision tasks. This section outlines a robust experimental setup to assess and mitigate these biases, ensuring models learn meaningful features rather than spurious correlations like background colors in classification tasks.\n\n### Core Experimental Framework\n\nThe primary goal is to construct an experiment that tests a model's ability to generalize across diverse scenarios, avoiding pitfalls like overfitting to irrelevant dataset features. Based on evidence from [ExploringCorruptionRob], models often exhibit performance drops under distribution shifts, with accuracy falling from 85% to 60% on corrupted vision datasets. To address this, the setup incorporates **cross-validation** and **distribution shift simulations** as statistical controls to quantify the impact of biases. The framework focuses on vision tasks, specifically classification problems like distinguishing apples from oranges, where biases toward background colors have been documented [NeuralAnisotropicView].\n\nThe experiment pipeline includes:\n- **Dataset Selection and Augmentation:** Use a balanced dataset with varied backgrounds, lighting conditions, and object orientations to minimize spurious correlations. Augment data with synthetic corruptions (e.g., noise, blur) to simulate real-world distribution shifts.\n- **Model Architecture:** Employ a standard convolutional neural network (CNN) as the baseline, given its prevalent use in vision tasks and documented susceptibility to texture bias [ExploringCorruptionRob].\n- **Training Protocol:** Train with a mix of standard and adversarially perturbed examples to encourage robustness. Implement early stopping based on validation performance across multiple distribution scenarios.\n- **Evaluation Metrics:** Beyond accuracy, track **robustness scores** under corrupted inputs and **feature attribution maps** to identify whether the model focuses on object shapes or irrelevant textures.\n\n### Bias Mitigation Strategies\n\nUnderstanding the specific ways models solve tasks is critical, as validation performance alone cannot guarantee robustness to naturally occurring shifts [NeuralAnisotropicView]. One approach is to integrate **brain-inspired inductive biases** into the architecture, such as those explored in recurrent vision models (C-RBP), which aim to prioritize shape over texture [DrewLinsleyBrown]. However, evidence suggests that encoding such biases for different object classes is highly challenging, if not nearly impossible, due to the underspecification of most machine learning pipelines [DrewLinsleyBrown]. Therefore, the experiment also tests data-centric interventions, like curated benchmarks that force generalization across diverse contexts (e.g., the classic 'dog in the park' example where background park features mislead classifiers).\n\n> **Key Finding:** Inductive biases, such as texture over shape preference, often lead to incorrect generalizations by exploiting spurious correlations, necessitating experimental designs that prioritize robustness over raw validation performance [ExploringCorruptionRob].\n\n### Execution and Monitoring\n\nExecution involves running the experiment across multiple seeds to account for variability in training outcomes, as highlighted by fluctuating validation metrics in prior studies [NeuralAnisotropicView]. Each run logs detailed metrics on a per-epoch basis, focusing on performance under synthetic corruptions. Monitoring tools visualize feature importance to detect bias early\u2014 for instance, if a model consistently attends to background colors in fruit classification, adjustments to data augmentation are triggered mid-training. This iterative process ensures the model learns transferable features.\n\n### Practical Considerations\n\nPractitioners must balance computational cost with experimental rigor. While extensive cross-validation and distribution shift testing are ideal, they can be resource-intensive. A practical compromise is to prioritize a subset of critical scenarios (e.g., common real-world corruptions like blur or low contrast) based on domain knowledge. Additionally, while architectural solutions for bias mitigation are appealing, their complexity often outweighs benefits, as noted in [DrewLinsleyBrown]. Data-driven approaches, though less elegant, frequently yield more immediate improvements in robustness for real-world deployment.\n\nThis setup provides a structured pathway to evaluate and address inductive biases, ensuring deep learning models generalize effectively in practical vision tasks.",
  "word_count": 620,
  "citations_used": [
    "[NeuralAnisotropicView]",
    "[ExploringCorruptionRob]",
    "[DrewLinsleyBrown]"
  ],
  "coverage_gaps": []
}
```

## Final Section Content (written prose)

Designing experiments to evaluate deep learning models requires meticulous attention to **inductive biases** that can skew generalization, such as a model's tendency to prioritize texture over shape in vision tasks. This section outlines a robust experimental setup to assess and mitigate these biases, ensuring models learn meaningful features rather than spurious correlations like background colors in classification tasks.

### Core Experimental Framework

The primary goal is to construct an experiment that tests a model's ability to generalize across diverse scenarios, avoiding pitfalls like overfitting to irrelevant dataset features. Based on evidence from [ExploringCorruptionRob], models often exhibit performance drops under distribution shifts, with accuracy falling from 85% to 60% on corrupted vision datasets. To address this, the setup incorporates **cross-validation** and **distribution shift simulations** as statistical controls to quantify the impact of biases. The framework focuses on vision tasks, specifically classification problems like distinguishing apples from oranges, where biases toward background colors have been documented [NeuralAnisotropicView].

The experiment pipeline includes:
- **Dataset Selection and Augmentation:** Use a balanced dataset with varied backgrounds, lighting conditions, and object orientations to minimize spurious correlations. Augment data with synthetic corruptions (e.g., noise, blur) to simulate real-world distribution shifts.
- **Model Architecture:** Employ a standard convolutional neural network (CNN) as the baseline, given its prevalent use in vision tasks and documented susceptibility to texture bias [ExploringCorruptionRob].
- **Training Protocol:** Train with a mix of standard and adversarially perturbed examples to encourage robustness. Implement early stopping based on validation performance across multiple distribution scenarios.
- **Evaluation Metrics:** Beyond accuracy, track **robustness scores** under corrupted inputs and **feature attribution maps** to identify whether the model focuses on object shapes or irrelevant textures.

### Bias Mitigation Strategies

Understanding the specific ways models solve tasks is critical, as validation performance alone cannot guarantee robustness to naturally occurring shifts [NeuralAnisotropicView]. One approach is to integrate **brain-inspired inductive biases** into the architecture, such as those explored in recurrent vision models (C-RBP), which aim to prioritize shape over texture [DrewLinsleyBrown]. However, evidence suggests that encoding such biases for different object classes is highly challenging, if not nearly impossible, due to the underspecification of most machine learning pipelines [DrewLinsleyBrown]. Therefore, the experiment also tests data-centric interventions, like curated benchmarks that force generalization across diverse contexts (e.g., the classic 'dog in the park' example where background park features mislead classifiers).

> **Key Finding:** Inductive biases, such as texture over shape preference, often lead to incorrect generalizations by exploiting spurious correlations, necessitating experimental designs that prioritize robustness over raw validation performance [ExploringCorruptionRob].

### Execution and Monitoring

Execution involves running the experiment across multiple seeds to account for variability in training outcomes, as highlighted by fluctuating validation metrics in prior studies [NeuralAnisotropicView]. Each run logs detailed metrics on a per-epoch basis, focusing on performance under synthetic corruptions. Monitoring tools visualize feature importance to detect bias early— for instance, if a model consistently attends to background colors in fruit classification, adjustments to data augmentation are triggered mid-training. This iterative process ensures the model learns transferable features.

### Practical Considerations

Practitioners must balance computational cost with experimental rigor. While extensive cross-validation and distribution shift testing are ideal, they can be resource-intensive. A practical compromise is to prioritize a subset of critical scenarios (e.g., common real-world corruptions like blur or low contrast) based on domain knowledge. Additionally, while architectural solutions for bias mitigation are appealing, their complexity often outweighs benefits, as noted in [DrewLinsleyBrown]. Data-driven approaches, though less elegant, frequently yield more immediate improvements in robustness for real-world deployment.

This setup provides a structured pathway to evaluate and address inductive biases, ensuring deep learning models generalize effectively in practical vision tasks.

