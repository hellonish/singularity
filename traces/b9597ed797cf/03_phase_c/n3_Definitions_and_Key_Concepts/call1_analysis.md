# `n3` — Definitions and Key Concepts
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
section_node_id: n3
section_title: Definitions and Key Concepts
section_description: Outlines essential terms like inductive bias and generalization, drawing on foundational texts to explain why models prefer certain patterns over others.
section_type: section
node_level: 2 / max_depth: 2
section_heading: #### Definitions and Key Concepts  (assembler adds this — do NOT include it in your content; use deeper levels for internal sub-headings)
audience: practitioner
research_query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method. Report Describing your Approach for Realizing the Project

## Retrieved Evidence

[Evidence 0 | Cite as: [InductiveBiasMachine]] Source: What Is Inductive Bias in Machine Learning? | Baeldung on Computer Science (https://www.baeldung.com/cs/ml-inductive-bias) | credibility=0.75
February 13, 2025 -Generally, every building block and every belief that we make about the data is a form of inductive bias. Inductive biasesplay an important role in the ability of machine learning models to generalize to the unseen data.

[Evidence 1 | Cite as: [InductiveBiasMachine2]] Source: What is Inductive Bias in Machine Learning? - GeeksforGeeks (https://www.geeksforgeeks.org/what-is-inductive-bias-in-machine-learning/) | credibility=0.75
June 25, 2024 -They prefer solutions where only a few features are relevant, which can improve interpretability and generalization. Inductive bias is crucial in machine learning as ithelps algorithms generalize from limited training data to unseen data.

[Evidence 2 | Cite as: [LearningInductiveBiase]] Source: Learning Inductive Biases with Simple Neural Networks (http://arxiv.org/abs/1802.02745v2) | credibility=1.00
People use rich prior knowledge about the world in order to efficiently learn new concepts. These priors - also known as "inductive biases" - pertain to the space of internal models considered by a learner, and they help the learner make inferences that go beyond the observed data. A recent study found that deep neural networks optimized for object recognition develop the shape bias (Ritter et al., 2017), an inductive bias possessed by children that plays an important role in early word learning

[Evidence 3 | Cite as: [LearningInductiveBiase2]] Source: Learning Inductive Biases with Simple Neural Networks (http://arxiv.org/abs/1802.02745v2) | credibility=1.00
People use rich prior knowledge about the world in order to efficiently learn new concepts. These priors - also known as "inductive biases" - pertain to the space of internal models considered by a learner, and they help the learner make inferences that go beyond the observed data. A recent study found that deep neural networks optimized for object recognition develop the shape bias (Ritter et al., 2017), an inductive bias possessed by children that plays an important role in early word learning

[Evidence 4 | Cite as: [InductiveBiasMachine3]] Source: Inductive Bias in Machine Learning (https://www.pickl.ai/blog/inductive-bias-in-machine-learning/) | credibility=0.75
Inductivebiasis crucialinensuring thatMachineLearningmodels canlearnefficiently and make reliable predictions even with limited information ...

[Evidence 5 | Cite as: [EmnlpHighlightsInducti]] Source: EMNLP 2018 Highlights: Inductive bias, cross-lingual learning, (https://www.ruder.io/emnlp-2018-highlights/) | credibility=0.75
Theinductivebiasof amachinelearningalgorithm is the set of assumptions that the model makesinorder to generalize to new inputs.

[Evidence 6 | Cite as: [DeepNeuralNetworks]] Source: Deep neural networks are lazy : on the inductive bias of deep learning (https://dspace.mit.edu/handle/1721.1/121680) | credibility=1.00
Although widely observed in practice, ... present evidence that deep neural networks have an inherent inductive bias thatmakes them inclined to learn generalizable hypotheses and avoid memorization....

[Evidence 7 | Cite as: [InductiveBiasesDeep]] Source: Inductive biases for deep learning of higher-level cognition | Proceedings A | The Royal Society (https://royalsocietypublishing.org/doi/10.1098/rspa.2021.0068) | credibility=0.75
October 1, 2022 -Our main hypothesis is that deep learning succeeded in part because of a set of inductive biases (preferences, priors or assumptions), but that additional ones should be included in order to go from good in-distribution generalization in highly ...

[Evidence 8 | Cite as: [InductivebiasWikipedia]] Source: Inductivebias- Wikipedia (https://en.wikipedia.org/wiki/Inductive_bias) | credibility=0.75
Theinductivebiasof a learning algorithm is the set of assumptions that the learner uses to predict outputs of given inputs that it has not encountered.Inductivebiasis anything which makes the algorithm learn one pattern instead of another pattern.

[Evidence 9 | Cite as: [InductiveBiasesDeep2]] Source: Inductive Biases in Deep Learning: Understanding Feature (https://www.marktechpost.com/2024/05/28/inductive-biases-in-deep-learning-understanding-feature-representation/) | credibility=0.75
...inductivebiastowards simplicityintheir architectures and ... Representationalbiasesmay relate to implicitinductivebiasesindeeplearning.

[Evidence 10 | Cite as: [ExplicitImplicitInduct]] Source: Explicit and Implicit Inductive Bias in Deep Learning Nati Srebro (TTIC) (https://www.itsoc.org/sites/default/files/2021-05/ITW2020+Tutorial+-+Explicit+and+Implicit+Inductive+Bias+in+Deep+Learning.pdf) | credibility=0.75
• Inductive Bias in Deep Learning:The Role of Implicit Optimization Bias· • The “complexity measure” approach for · understanding Deep Learning · (break) • Examples of Identifying the Implicit Bias and · “complexity measure” · • Squared Loss vs Logistic Loss ·



## Raw LLM Response

```
{
  "call": 1,
  "section_node_id": "n3",
  "tier2_selected": ["synthesis", "claim_verification", "quality_check"],
  "analyses": {
    "synthesis": "Synthesised finding: Inductive bias in machine learning refers to the inherent assumptions or preferences that guide models to favor certain generalizations over others, enabling efficient learning from limited data, as evidenced by definitions across sources that emphasize its role in generalization, such as preferring simple features or shape-based priors in neural networks.",
    "claim_verification": "Claims verified: Inductive bias helps models generalize to unseen data [InductiveBiasMachine, InductiveBiasMachine2, InductivebiasWikipedia]; Deep neural networks develop inductive biases like shape preference [LearningInductiveBiase]; Refuted: No direct refutations, but some claims lack empirical backing beyond theoretical assertions.",
    "quality_check": "Evidence quality assessment: High-quality sources include peer-reviewed arxiv papers [LearningInductiveBiase] with credibility 1.00, providing robust empirical insights; general blog posts [InductiveBiasMachine] at 0.75 offer accessible but less rigorous explanations, with potential for bias due to non-academic origins."
  },
  "key_evidence_chunks": [0, 2, 8],
  "citations_found": ["[InductiveBiasMachine]", "[LearningInductiveBiase]", "[InductivebiasWikipedia]"],
  "coverage_gaps": ["No detailed experiments on incorrect inductive biases in vision domains, such as models confusing background colors with object classes", "Limited specific solutions from literature for addressing incorrect biases in deep learning", "Missing quantitative metrics for evaluating bias correction methods in language domains"],
  "single_source_warning": null
}
```

## Parsed JSON

```json
{
  "call": 1,
  "section_node_id": "n3",
  "tier2_selected": [
    "synthesis",
    "claim_verification",
    "quality_check"
  ],
  "analyses": {
    "synthesis": "Synthesised finding: Inductive bias in machine learning refers to the inherent assumptions or preferences that guide models to favor certain generalizations over others, enabling efficient learning from limited data, as evidenced by definitions across sources that emphasize its role in generalization, such as preferring simple features or shape-based priors in neural networks.",
    "claim_verification": "Claims verified: Inductive bias helps models generalize to unseen data [InductiveBiasMachine, InductiveBiasMachine2, InductivebiasWikipedia]; Deep neural networks develop inductive biases like shape preference [LearningInductiveBiase]; Refuted: No direct refutations, but some claims lack empirical backing beyond theoretical assertions.",
    "quality_check": "Evidence quality assessment: High-quality sources include peer-reviewed arxiv papers [LearningInductiveBiase] with credibility 1.00, providing robust empirical insights; general blog posts [InductiveBiasMachine] at 0.75 offer accessible but less rigorous explanations, with potential for bias due to non-academic origins."
  },
  "key_evidence_chunks": [
    0,
    2,
    8
  ],
  "citations_found": [
    "[InductiveBiasMachine]",
    "[LearningInductiveBiase]",
    "[InductivebiasWikipedia]"
  ],
  "coverage_gaps": [
    "No detailed experiments on incorrect inductive biases in vision domains, such as models confusing background colors with object classes",
    "Limited specific solutions from literature for addressing incorrect biases in deep learning",
    "Missing quantitative metrics for evaluating bias correction methods in language domains"
  ],
  "single_source_warning": null
}
```

