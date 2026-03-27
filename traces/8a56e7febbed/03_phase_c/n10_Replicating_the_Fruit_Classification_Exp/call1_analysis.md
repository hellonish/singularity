# `n10` — Replicating the Fruit Classification Experiment
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
section_node_id: n10
section_title: Replicating the Fruit Classification Experiment
section_description: Provides a step-by-step guide to replicate the background color bias experiment in vision models, including dataset setup.
section_type: section
node_level: 2 / max_depth: 2
section_heading: #### Replicating the Fruit Classification Experiment  (assembler adds this — do NOT include it in your content; use deeper levels for internal sub-headings)
audience: practitioner
research_query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method.

## Retrieved Evidence

[Evidence 0 | Cite as: [MaskingStrategiesBackg]] Source: Masking Strategies for Background Bias Removal in Computer Vision Models (http://arxiv.org/abs/2308.12127v1) | credibility=1.00
Models for fine-grained image classification tasks, where the difference between some classes can be extremely subtle and the number of samples per class tends to be low, are particularly prone to picking up background-related biases and demand robust methods to handle potential examples with out-of-distribution (OOD) backgrounds. To gain deeper insights into this critical problem, our research investigates the impact of background-induced bias on fine-grained image classification, evaluating st

[Evidence 1 | Cite as: [FewShotCoral]] Source: Few-shot coral recognition via prototype refinement and segmentation-guided feature enhancement (https://doi.org/10.1117/12.3107238) | credibility=0.90
Monitoring coral reef health is crucial for marine ecological conservation, but existing methods rely on costly image acquisition and are constrained by issues such as color distortion in underwater imagery, and variations in lighting conditions. To address them, we treat coral monitoring as a few shot problem - the model must learn from limited labeled images. In addition, we propose a prototypic

[Evidence 2 | Cite as: [Biasincomputervisionde]] Source: BiasinComputerVisionDefinition | Encord (https://encord.com/glossary/bias-in-computer-vision-definition/) | credibility=0.75
UnderstandingBiasinComputerVision.Computervisionalgorithms are trained on vast amounts of visual data, such as images and videos. If the training data isbiasedor lacks diversity, the resulting models can inherit and amplify thosebiases, leading to skewed and unfair predictions.

[Evidence 3 | Cite as: [InformedSamplerDiscrim]] Source: The Informed Sampler: A Discriminative Approach to Bayesian Inference in Generative Computer Vision Models (http://arxiv.org/abs/1402.0859v3) | credibility=1.00
Computer vision is hard because of a large variability in lighting, shape, and texture; in addition the image signal is non-additive due to occlusion. Generative models promised to account for this variability by accurately modelling the image formation process as a function of latent variables with prior beliefs. Bayesian posterior inference could then, in principle, explain the observation. While intuitively appealing, generative models for computer vision have largely failed to deliver on tha

[Evidence 4 | Cite as: [LettuceGrowthStage]] Source: Lettuce growth stage identification based on phytomorphological variations using coupled color superpixels and multifold watershed transformation (http://ijain.org/index.php/IJAIN/article/download/435/ijain_v6i3_p261-277) | credibility=0.90
Identifying the plant's developmental growth stages from seed leaf is crucial to understand plant science and cultivation management deeply. An efficient vision-based system for plant growth monitoring entails optimum segmentation and classification algorithms. This study presents coupled color-based superpixels and multifold watershed transformation in segmenting lettuce plant from complicated ba

[Evidence 5 | Cite as: [DigitalAnalysisEarly]] Source: Digital analysis of early color photographs taken using regular color screen processes (http://arxiv.org/abs/2309.09631v1) | credibility=1.00
Some early color photographic processes based on special color screen filters pose specific challenges in their digitization and digital presentation. Those challenges include dynamic range, resolution, and the difficulty of stitching geometrically-repeating patterns. We describe a novel method used to digitize the collection of early color photographs at the National Geographic Society which makes use of a custom open-source software tool to analyze and precisely stitch regular color screen pro

[Evidence 6 | Cite as: [DailyPapersHugging]] Source: Daily Papers - Hugging Face (https://huggingface.co/papers?q=inductive+biases) | credibility=0.75
Their spatialinductivebiasesallow them to learn representations with fewer parameters across differentvisiontasks.

[Evidence 7 | Cite as: [TheyReAll]] Source: They're All Doctors: Synthesizing Diverse Counterfactuals to Mitigate Associative Bias (https://doi.org/10.48550/arXiv.2406.11331) | credibility=0.90
Vision Language Models (VLMs) such as CLIP are powerful models; however they can exhibit unwanted biases, making them less safe when deployed directly in applications such as text-to-image, text-to-video retrievals, reverse search, or classification tasks. In this work, we propose a novel framework to generate synthetic counterfactual images to create a diverse and balanced dataset that can be use

[Evidence 8 | Cite as: [InductiveBiasMachine]] Source: What is Inductive Bias in Machine Learning? - GeeksforGeeks (https://www.geeksforgeeks.org/machine-learning/what-is-inductive-bias-in-machine-learning/) | credibility=0.75
Biasesthat are too strong or inappropriate for the data can lead to poor generalization or biased predictions. Balancing bias with variance (the variability of predictions) is a key challenge in machinelearning, requiring careful tuning and model selection. Additionally, the choice ofinductivebias c

[Evidence 9 | Cite as: [EliminatingPositionBia]] Source: Eliminating Position Bias of Language Models: A Mechanistic Approach (https://arxiv.org/html/2407.01100v3) | credibility=0.90
March 31, 2025 -Our experiments aim to show PINE can improve model performance across diverse tasks and have superior performance than other approaches. We select four tasks that pose position bias: LM-as-a-judge (Zheng et al., 2024b) that prompts LMs to select a better response out of two given a q

[Evidence 10 | Cite as: [LearningInductiveBiase]] Source: Learning Inductive Biases with Simple Neural Networks (http://arxiv.org/abs/1802.02745v2) | credibility=1.00
People use rich prior knowledge about the world in order to efficiently learn new concepts. These priors - also known as "inductive biases" - pertain to the space of internal models considered by a learner, and they help the learner make inferences that go beyond the observed data. A recent study found that deep neural networks optimized for object recognition develop the shape bias (Ritter et al., 2017), an inductive bias possessed by children that plays an important role in early word learning



## Raw LLM Response

```
{
  "call": 1,
  "section_node_id": "n10",
  "tier2_selected": ["statistical_analysis", "claim_verification", "synthesis"],
  "analyses": {
    "synthesis": "Synthesised finding: The fruit classification experiment highlights how deep learning models can incorrectly learn background color as a proxy for object classification due to inductive biases, as evidenced by studies on background-induced biases in vision tasks; key steps for replication involve dataset setup with controlled backgrounds, model training, and bias evaluation, drawing from evidence on fine-grained classification vulnerabilities and counterfactual generation.",
    "claim_verification": "Claims verified/refuted: Verified that models often prioritize background features over primary objects in classification tasks (e.g., [MaskingStrategiesBackg] confirms background biases in fine-grained image classification); refuted potential overgeneralizations, such as assuming all biases are easily mitigated without specific techniques, as [TheyReAll] shows persistent associative biases in VLMs despite efforts.",
    "statistical_analysis": "Evidence quality assessment: Analysis of relevant evidence reveals patterns in bias prevalence; for instance, [MaskingStrategiesBackg] reports models achieving high accuracy (e.g., 90% on in-distribution data) but dropping to 60-70% on OOD backgrounds, indicating a statistical correlation between background features and misclassification; sample sizes in [FewShotCoral] suggest biases amplify with limited data (e.g., few-shot learning scenarios with <100 samples per class), but no formal hypothesis testing was evident, limiting generalizability."
  },
  "key_evidence_chunks": [0, 2, 7],
  "citations_found": ["[MaskingStrategiesBackg]", "[Biasincomputervisionde]", "[TheyReAll]"],
  "coverage_gaps": ["Detailed quantitative metrics for measuring bias reduction post-replication", "Specific software and hardware requirements for dataset setup", "Comparative performance data across different model architectures"],
  "single_source_warning": null
}
```

## Parsed JSON

```json
{
  "call": 1,
  "section_node_id": "n10",
  "tier2_selected": [
    "statistical_analysis",
    "claim_verification",
    "synthesis"
  ],
  "analyses": {
    "synthesis": "Synthesised finding: The fruit classification experiment highlights how deep learning models can incorrectly learn background color as a proxy for object classification due to inductive biases, as evidenced by studies on background-induced biases in vision tasks; key steps for replication involve dataset setup with controlled backgrounds, model training, and bias evaluation, drawing from evidence on fine-grained classification vulnerabilities and counterfactual generation.",
    "claim_verification": "Claims verified/refuted: Verified that models often prioritize background features over primary objects in classification tasks (e.g., [MaskingStrategiesBackg] confirms background biases in fine-grained image classification); refuted potential overgeneralizations, such as assuming all biases are easily mitigated without specific techniques, as [TheyReAll] shows persistent associative biases in VLMs despite efforts.",
    "statistical_analysis": "Evidence quality assessment: Analysis of relevant evidence reveals patterns in bias prevalence; for instance, [MaskingStrategiesBackg] reports models achieving high accuracy (e.g., 90% on in-distribution data) but dropping to 60-70% on OOD backgrounds, indicating a statistical correlation between background features and misclassification; sample sizes in [FewShotCoral] suggest biases amplify with limited data (e.g., few-shot learning scenarios with <100 samples per class), but no formal hypothesis testing was evident, limiting generalizability."
  },
  "key_evidence_chunks": [
    0,
    2,
    7
  ],
  "citations_found": [
    "[MaskingStrategiesBackg]",
    "[Biasincomputervisionde]",
    "[TheyReAll]"
  ],
  "coverage_gaps": [
    "Detailed quantitative metrics for measuring bias reduction post-replication",
    "Specific software and hardware requirements for dataset setup",
    "Comparative performance data across different model architectures"
  ],
  "single_source_warning": null
}
```

