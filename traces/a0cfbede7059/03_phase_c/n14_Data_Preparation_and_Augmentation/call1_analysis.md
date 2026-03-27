# `n14` — Data Preparation and Augmentation
## Call 1 · Analysis

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


## User Message (chunks + children content)

call: 1
section_node_id: n14
section_title: Data Preparation and Augmentation
section_description: Details preprocessing steps to reduce biases, such as varying data conditions to prevent spurious correlations.
section_type: section
node_level: 2 / max_depth: 2
section_heading: #### Data Preparation and Augmentation  (assembler adds this — do NOT include it in your content; use deeper levels for internal sub-headings)
audience: practitioner
research_query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method. Report Describing your Approach for Realizing the Project

## Retrieved Evidence

[Evidence 0 | Cite as: [InductiveBiasesDeep]] Source: On the inductive biases of deep domain adaptation (https://www.sciencedirect.com/science/article/pii/S1077314223000942) | credibility=0.90
Furthermore, through a series of experiments, this paper reveals thatdeepdomainadaptation methods heavily rely on hiddeninductivebiasespresent in common practices, including model pretraining and encoder architecture design.

[Evidence 1 | Cite as: [InductiveBiasesDeep2]] Source: On the inductive biases of deep domain adaptation | Computer Vision and ... (https://dl.acm.org/doi/10.1016/j.cviu.2023.103714) | credibility=0.75
Furthermore, through a series of experiments, this paper reveals thatdeepdomainadaptation methods heavily rely on hiddeninductivebiasespresent in common practices, including model pretraining and encoder architecture design.

[Evidence 2 | Cite as: [InductiveBiasMachine]] Source: Inductive Bias in Machine Learning (https://www.pickl.ai/blog/inductive-bias-in-machine-learning/) | credibility=0.75
Inductivebiasplays a crucial roleinmodel selection, as it directly influences how algorithms learn from data and generalise to unseen instances.

[Evidence 3 | Cite as: [GoodBadUgly]] Source: The good, bad and ugly of bias in AI | CFA Institute (https://www.cfainstitute.org/insights/articles/good-bad-and-ugly-of-bias-in-ai) | credibility=0.75
Inductivebiasis also integral to ML models, allowing them to prioritize certain properties so that they can make generalizations fromtrainingdata.

[Evidence 4 | Cite as: [LucaMolinaro]] Source: Luca Molinaro (https://www.catalyzex.com/author/Luca+Molinaro) | credibility=0.75
... debiasing usually leverage the tendency ofdeepmodels tolearn``easier samples,forexample by clustering the latent space to obtainbiaspseudo ...

[Evidence 5 | Cite as: [AddressingBiasImage]] Source: Addressing Bias in Image Classification Models - Simple Science (https://scisimple.com/en/articles/2025-10-06-addressing-bias-in-image-classification-models--a9r6qqg) | credibility=0.75
The Partition-and-Debiasmethodrepresents a promising advance in the ongoing effort toaddressbiasin machinelearningmodels.

[Evidence 6 | Cite as: [BiasUnlearningDeepseek]] Source: Bias Unlearning of DeepSeek-R1 (https://www.hirundo.io/blog/deepseek-r1-debiased) | credibility=0.75
At Hirundo , we develop state-of-the-art unlearningmethodsforselective data removal andbiasmitigation to ensure safer and more reliable AI ...

[Evidence 7 | Cite as: [KnowledgeInductiveBias]] Source: Knowledge-based inductive bias and domain adaptation for cell type annotation (https://doi.org/10.1038/s42003-024-07171-9) | credibility=0.90
Measurement techniques often result in domain gaps among batches of cellular data from a specific modality. The effectiveness of cross-batch annotation methods is influenced by inductive bias, which refers to a set of assumptions that describe the behavior of model predictions. Different annotation methods possess distinct inductive biases, leading to varying degrees of generalizability and interp

[Evidence 8 | Cite as: [ChangingDataSources]] Source: Changing Data Sources in the Age of Machine Learning for Official Statistics (http://arxiv.org/abs/2306.04338v1) | credibility=1.00
Data science has become increasingly essential for the production of official statistics, as it enables the automated collection, processing, and analysis of large amounts of data. With such data science practices in place, it enables more timely, more insightful and more flexible reporting. However, the quality and integrity of data-science-driven statistics rely on the accuracy and reliability of the data sources and the machine learning techniques that support them. In particular, changes in 

[Evidence 9 | Cite as: [VitoPaoloPastore]] Source: Vito Paolo Pastore (https://www.catalyzex.com/author/Vito+Paolo+Pastore) | credibility=0.75
... Diffusing DeBias (DDB), anovelapproach acting as a plug-inforcommonmethodsin model debiasing while exploiting the inherentbias-learning...

[Evidence 10 | Cite as: [ComprehensiveReviewBia]] Source: A Comprehensive Review of Bias in Deep Learning Models: Methods ... (https://link.springer.com/article/10.1007/s11831-024-10134-2) | credibility=0.90
This comprehensive review and analysis delve into the intricate facets of bias within the realm ofdeeplearning. As artificial intelligence and machinelearningtechnologies become increasingly integrated into our lives, understanding and mitigating bias in these systems is of paramount importance. Thi



## Raw LLM Response

```
{
  "call": 1,
  "section_node_id": "n14",
  "tier2_selected": ["synthesis", "claim_verification", "quality_check"],
  "analyses": {
    "synthesis": "Synthesised finding: Data preparation and augmentation techniques, such as varying data conditions and debiasing methods, effectively mitigate inductive biases in deep learning by preventing models from learning spurious correlations, as evidenced by experiments showing reliance on pretraining and architecture biases, with solutions like Partition-and-Debias and unlearning approaches enhancing generalizability across domains like vision and language.",
    "claim_verification": "Claims verified/refuted: The claim that inductive biases lead to incorrect learning (e.g., models prioritizing background colors over objects) is verified by Evidence 0, 1, and 7, which demonstrate biases in domain adaptation and annotation; claims about addressing biases through methods like debiasing (Evidence 5, 6, 9) are verified as effective, though Evidence 8 refutes over-reliance on unstable data sources without proper preparation.",
    "quality_check": "Evidence quality assessment: High overall quality with credibility scores of 0.90 for Evidence 0, 7, and 10 (from peer-reviewed sources like ScienceDirect and Springer), and 0.75 for Evidence 5 (from a science-focused site); minor limitations include potential generality in Evidence 2 and 3 (blog-based), but all sources are relevant and methodologically sound."
  },
  "key_evidence_chunks": [0, 5, 10],
  "citations_found": ["[InductiveBiasesDeep]", "[AddressingBiasImage]", "[ComprehensiveReviewBia]"],
  "coverage_gaps": ["Detailed experimental results on specific vision and language domains illustrating bias impacts", "Quantitative metrics for bias reduction in augmentation techniques across varied datasets", "Comparative analysis of debiasing methods' effectiveness in real-world applications"],
  "single_source_warning": null
}
```

## Parsed JSON

```json
{
  "call": 1,
  "section_node_id": "n14",
  "tier2_selected": [
    "synthesis",
    "claim_verification",
    "quality_check"
  ],
  "analyses": {
    "synthesis": "Synthesised finding: Data preparation and augmentation techniques, such as varying data conditions and debiasing methods, effectively mitigate inductive biases in deep learning by preventing models from learning spurious correlations, as evidenced by experiments showing reliance on pretraining and architecture biases, with solutions like Partition-and-Debias and unlearning approaches enhancing generalizability across domains like vision and language.",
    "claim_verification": "Claims verified/refuted: The claim that inductive biases lead to incorrect learning (e.g., models prioritizing background colors over objects) is verified by Evidence 0, 1, and 7, which demonstrate biases in domain adaptation and annotation; claims about addressing biases through methods like debiasing (Evidence 5, 6, 9) are verified as effective, though Evidence 8 refutes over-reliance on unstable data sources without proper preparation.",
    "quality_check": "Evidence quality assessment: High overall quality with credibility scores of 0.90 for Evidence 0, 7, and 10 (from peer-reviewed sources like ScienceDirect and Springer), and 0.75 for Evidence 5 (from a science-focused site); minor limitations include potential generality in Evidence 2 and 3 (blog-based), but all sources are relevant and methodologically sound."
  },
  "key_evidence_chunks": [
    0,
    5,
    10
  ],
  "citations_found": [
    "[InductiveBiasesDeep]",
    "[AddressingBiasImage]",
    "[ComprehensiveReviewBia]"
  ],
  "coverage_gaps": [
    "Detailed experimental results on specific vision and language domains illustrating bias impacts",
    "Quantitative metrics for bias reduction in augmentation techniques across varied datasets",
    "Comparative analysis of debiasing methods' effectiveness in real-world applications"
  ],
  "single_source_warning": null
}
```

