# `n11` — Incorrect Biases in Language Domains
## Call 1 · Analysis

## System Prompt

# REPORT WORKER — PARENT SECTION

You are a research writer producing ONE parent section. Your children sections are
already written. Your job is to write a **thesis**, not a summary.

## What a thesis means here

A thesis is a claim that only becomes visible by seeing the children together.
It names the unifying insight, tension, or pattern that no single child reveals alone.
The reader encounters your section BEFORE the children — it must stand alone as an
intellectual contribution, not as a table of contents.

**Domain language rule (Issue 11):** Write as a domain expert would in a research
paper. Never use meta-language that describes the report structure.

✗ BAD (meta-language):
- "This chapter examines three approaches to the problem..."
- "The following subsections provide an overview of..."
- "The sections below cover FFT complexity, applications, and limitations."
- "This chapter will explore the relationship between..."

✓ GOOD (domain language):
- "Spectral decomposition achieves its $O(N \log N)$ efficiency by exploiting
  symmetry — a principle that recurs across every application examined here."
- "The gap between theoretical bounds and implementation performance narrows
  precisely where hardware exploits the algorithm's recursive structure."
- "Three generations of transformer scaling share a single limiting factor: the
  quadratic cost of full self-attention."

**Self-check before writing:** Read your opening sentence. Does it contain the words
"chapter", "section", "covers", "explores", "examines", "provides", "presents",
"discusses", or "will"? If yes, rewrite it as a domain-language claim.

## Context You Receive

- Your section's title and description
- The full written content of all your direct children (in order)
- A small number of Qdrant chunks (cross-cutting evidence not covered by any child)

## Your Two-Step Task

### Step 1 — Multi-Analysis (Call 1)

Run three analyses over the children content using:

synthesis            — identify the overarching thesis claim across all children
theme_extraction     — extract 2–4 cross-cutting themes that span multiple children
                       (a theme must appear in ≥2 children to count)
comparative_analysis — identify tensions, contrasts, or progressions across children

**Do NOT run `gap_analysis` at the parent level.** Each leaf already identified its
own coverage gaps — repeating them here creates noise. The parent's job is to find
what emerges at the intersection of children, not to audit their gaps.

The `theme_extraction` output should list each theme as:
  "theme_name: how it manifests across child 1, child 2 (and optionally child 3)"

### Step 2 — Section Write (Call 2)

Write the parent section as a thesis introduction. Rules:

1. **Opening sentence** = the thesis claim. State it directly in domain language.
   (see ✓ GOOD examples above)
2. **Body** (2–3 sentences each, tight):
   - Signal the cross-cutting theme that unifies the children
   - Name the tension or progression if comparative_analysis found one
   - One sentence per child: what unique contribution each child makes
     (stated as a domain insight, not "Section X covers Y")
3. **Closing** = the `> **Key Insight:**` blockquote with the single most important
   cross-cutting insight that only this level can surface.
4. **Length: 200–350 words.** Every sentence must earn its place.
5. Do NOT summarise children in detail — readers will read them directly.
6. Do NOT introduce new factual claims not grounded in the provided evidence.

## Output Format

Respond ONLY with this JSON.

### Call 1 Response:
```json
{
  "call": 1,
  "section_node_id": "n5",
  "tier2_selected": ["synthesis", "theme_extraction", "comparative_analysis"],
  "analyses": {
    "synthesis": "Thesis claim: ...",
    "theme_extraction": "Theme 1 — name: manifests in child A as X, child B as Y. Theme 2 — ...",
    "comparative_analysis": "Key tension or progression across children: ..."
  },
  "citations_found": ["[Smith2024]"],
  "key_evidence_chunks": []
}
```

### Call 2 Response:
```json
{
  "call": 2,
  "section_node_id": "n5",
  "section_title": "...",
  "tier3_selected": "exec_summary",
  "content": "Domain-language thesis sentence. Cross-cutting theme paragraph. Child contribution signals. \n\n> **Key Insight:** The single insight only visible at this level.",
  "word_count": 250,
  "citations_used": ["[Smith2024]"],
  "coverage_gaps": []
}
```

## JSON Encoding Rules — READ FIRST

Your response is a JSON object. String values in JSON have strict encoding rules.

**Critical: never put a literal newline inside a JSON string value.**
Use escape sequences:

| You want | Write in JSON string |
|---|---|
| New paragraph | `\n\n` |
| Line break within a block | `\n` |
| Horizontal rule | `\n\n---\n\n` |
| Bullet list item | `\n- item` |
| Blockquote | `\n\n> **Key Insight:** text\n\n` |
| Sub-heading | `\n\n### Title\n\n` |

Every LaTeX backslash must be doubled in a JSON string: `\\sum`, `\\frac`, `\\text`.
Matrix row breaks are `\\` in LaTeX — inside JSON that becomes `\\\\` (four chars).
`"\\begin{bmatrix} 1 & 0 \\\\ 0 & 1 \\end{bmatrix}"` ← correct matrix in JSON.

**Correct example:**
```json
"content": "Encoder and decoder layers form two complementary halves of the Transformer.\n\n- The **encoder** processes the full input sequence bidirectionally, producing a rich contextual representation $H \\in \\mathbb{R}^{N \\times d}$.\n- The **decoder** generates output tokens autoregressively, attending to $H$ via cross-attention.\n\n> **Key Insight:** The encoder's bidirectional access vs. the decoder's causal masking is not a limitation but a deliberate design: it enables the same architecture to serve both classification (encoder-only) and generation (decoder-only) tasks."
```

## Writing Rules

### Structure
1. Do NOT begin `content` with the section heading — the assembler injects it.
2. The opening sentence must be a **domain-language claim**, not a question and not
   a description of what the chapter covers (see ✗ BAD / ✓ GOOD examples above).
3. Parent sections are concise: **200–350 words**. Every sentence must earn its place.

### Math and symbols — CRITICAL
4. **All mathematical expressions MUST use KaTeX syntax.**
   - Inline: `$O(N^2)$`, `$x[n]$`, `$\omega$`
   - Display: `$$X[k] = \sum_{n=0}^{N-1} x[n]\, e^{-j2\pi kn/N}$$`
   - Never write math as plain text. `O(N²)` is wrong; `$O(N^2)$` is correct.
   - Greek letters: `$\alpha$`, `$\omega$` — never unicode (α, ω) in math context.

   **FORBIDDEN math delimiters — these will NOT render:**
   - `\(x = y\)` — NOT supported. Use `$x = y$`.
   - `\[x = y\]` — NOT supported. Use `$$x = y$$`.
   - Plain parentheses `(x = y)` around math are plain text, not rendered.

### Formatting
5. **Bold** (`**term**`) the first occurrence of any technical term introduced at
   this level that was not already bolded in a child section.
6. If synthesising a list of distinct contributions, a tight bullet list is appropriate.
   Otherwise write prose.

   **TABLE FORMAT — CRITICAL. Multi-line with `\n` between each row in JSON string:**
   ```json
   "content": "Summary:\n\n| Aspect | Detail |\n|--------|--------|\n| Row A  | Value  |\n\nFurther..."
   ```
   NEVER write all table rows on one line. The `|---|` separator row is required.

7. Use a `> **Key Insight:**` blockquote for the single cross-cutting insight that
   only this level can surface.

### Evidence and citations
8. No new factual claims without a citation — if you add something, it must come
   from the provided evidence items. Use pre-assigned citation keys verbatim.
9. **NEVER write "Evidence X", "Chunk X", or any reference to internal index numbers
   in your content.** Use only the bracketed citation key: `[Smith2024]`.
10. Do NOT re-introduce facts already cited in children. Cross-cutting insight only.

### Narrative voice
11. Banned filler phrases:
    - "Overall, ..." / "In summary, ..." as paragraph openers
    - "By leveraging..."
    - "It is worth noting that..."
    - "Underscores the importance of..."
    - "Highlights the fact that..."
12. Write for the stated audience. Match technical depth to what children established.


## User Message (chunks + children content)

call: 1
section_node_id: n11
section_title: Incorrect Biases in Language Domains
section_description: Addresses language-specific biases such as positional overfitting in NLP, extending the problem-driven approach to new domains.
section_type: chapter
node_level: 1 / max_depth: 2
section_heading: ### Incorrect Biases in Language Domains  (assembler adds this — do NOT include it in your content; use deeper levels for internal sub-headings)
audience: practitioner
research_query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method. Report Describing your Approach for Realizing the Project

## Retrieved Evidence

[Evidence 0 | Cite as: [LiangDingAcl]] Source: Liang Ding - ACL Anthology (https://aclanthology.org/people/liang-ding/) | credibility=0.75
Experimentson 7 natural language understanding (NLU) tasks show that our ICCD method brings consistent and significant improvement (upto +1.8 ...

[Evidence 1 | Cite as: [SequenceSequenceLearni]] Source: Sequence-to-Sequence Learning as Beam-Search Optimization (https://www.aclweb.org/anthology/D16-1137.pdf) | credibility=0.95
Sequence-to-Sequence (seq2seq) modeling has rapidly become an important general-purpose NLP tool that has proven effective for many text-generation and sequence-labeling tasks. Seq2seq builds on deep neural language modeling and inherits its remarkable accuracy in estimating local, next-word distributions. In this work, we introduce a model and beam-search training scheme, based on the work of Dau

[Evidence 2 | Cite as: [AnalysingImpactSequenc]] Source: Analysing The Impact of Sequence Composition on Language Model Pre-Training (http://arxiv.org/abs/2402.13991v1) | credibility=1.00
Most language model pre-training frameworks concatenate multiple documents into fixed-length sequences and use causal masking to compute the likelihood of each token given its context; this strategy is widely adopted due to its simplicity and efficiency. However, to this day, the influence of the pre-training sequence composition strategy on the generalisation properties of the model remains under-explored. In this work, we find that applying causal masking can lead to the inclusion of distracti

[Evidence 3 | Cite as: [ContextInductiveBiases]] Source: The in-context inductive biases of vision-language models differ across modalities (https://www.researchgate.net/publication/388685854_The_in-context_inductive_biases_of_vision-language_models_differ_across_modalities) | credibility=0.75
February 7, 2025 -Download Citation | The in-context inductive biases of vision-language models differ across modalities |Inductive biases are what allow learners to make guesses in the absence of conclusive evidence.

[Evidence 4 | Cite as: [OverfittingNlpwithDeep]] Source: Overfitting|NLPwith Deep Learning (https://kh-kim.github.io/nlp_with_deep_learning_blog/docs/1-12-how-to-prevent-overfitting/02-overfitting/) | credibility=0.75
Introduction toNLP. What isNLP.NLPwith Deep Learning.NLPvs Others.PositionalEncoding Exercise. Implement Inference.

[Evidence 5 | Cite as: [LearningInductiveBiase]] Source: Learning Inductive Biases with Simple Neural Networks (http://arxiv.org/abs/1802.02745v2) | credibility=1.00
People use rich prior knowledge about the world in order to efficiently learn new concepts. These priors - also known as "inductive biases" - pertain to the space of internal models considered by a learner, and they help the learner make inferences that go beyond the observed data. A recent study found that deep neural networks optimized for object recognition develop the shape bias (Ritter et al., 2017), an inductive bias possessed by children that plays an important role in early word learning

[Evidence 6 | Cite as: [LearningInductiveBiase2]] Source: Learning Inductive Biases with Simple Neural Networks (http://arxiv.org/abs/1802.02745v2) | credibility=1.00
People use rich prior knowledge about the world in order to efficiently learn new concepts. These priors - also known as "inductive biases" - pertain to the space of internal models considered by a learner, and they help the learner make inferences that go beyond the observed data. A recent study found that deep neural networks optimized for object recognition develop the shape bias (Ritter et al., 2017), an inductive bias possessed by children that plays an important role in early word learning

[Evidence 7 | Cite as: [ResponsibleAiNlp]] Source: Responsible AI in NLP: GUS-Net Span-Level Bias Detection (https://arxiv.org/html/2410.08388v5) | credibility=0.90
Datasetssuch as NBIAS [ 21 ] and the MediaBiasAnnotation Corpus [ 22 ] provide single “BIAS” tags at the token level, sometimeswithcoarse ...

[Evidence 8 | Cite as: [LanguageModelsLearn]] Source: How do language models learn facts? Dynamics, curricula and hallucinations (http://arxiv.org/abs/2503.21676v2) | credibility=1.00
Large language models accumulate vast knowledge during pre-training, yet the dynamics governing this acquisition remain poorly understood. This work investigates the learning dynamics of language models on a synthetic factual recall task, uncovering three key findings: First, language models learn in three phases, exhibiting a performance plateau before acquiring precise factual knowledge. Mechanistically, this plateau coincides with the formation of attention-based circuits that support recall.

## Children Content (already written)

### Positional Bias in Text Classification

Deep learning models in text classification often overfit to positional features, such as word order or sequence indices, at the expense of semantic understanding, leading to poor generalization. This **positional bias** emerges when models rely on spurious correlations, like fixed positions in embeddings or sequence composition, rather than meaningful linguistic patterns. Practitioners must recognize this issue as a critical barrier to robust model performance, especially in real-world applications where data distributions shift unpredictably.

### Understanding Positional Bias

Positional bias occurs when models prioritize low-level features, such as the absolute position of words in a sequence, over higher-level semantic content. Studies show that architectures like neural networks with **Flatten layers** create rigid dependencies on these coordinates, causing the model to overfit to training data patterns that do not generalize [OverfittingNlpwithDeep]. This is analogous to vision models overfitting to background colors rather than object features—a problem of misplaced focus. The implication for practitioners is clear: models may perform well on benchmark datasets but fail in production environments with varied input structures.

### Causal Roots in Model Design

The root cause of positional bias often lies in the architecture and training strategies employed. For instance, **causal masking** in pre-training, where multiple documents are concatenated into fixed-length sequences, introduces distractions that lead models to make incorrect inferences based on positional cues rather than context [AnalysingImpactSequenc]. This strategy, while efficient, compromises generalization by embedding biases unrelated to the task. As a practitioner, understanding that this issue stems from design choices—not inherent data properties—can guide mitigation efforts during model development.

### Mitigation Strategies

Addressing positional bias requires intentional design to enforce robust priors. One promising approach is the use of **auxiliary losses** alongside the main objective function to guide the model toward better representations [TailoringEncodingInduc]. Although effective in some domains, this method is not without challenges; since auxiliary losses are optimized only on training data, they can still suffer from generalization gaps. Practitioners should experiment with tailored objectives specific to text classification, ensuring that validation includes diverse sequence structures to test robustness.

> **Key Finding:** Positional bias in text classification models often results from over-reliance on sequence positions rather than semantic content, necessitating architectural adjustments and tailored training objectives to improve generalization [OverfittingNlpwithDeep].

### Practical Implications

For those deploying text classification systems, positional bias can manifest as unexpected failures when input formats deviate from training data. Consider a sentiment analysis model trained on reviews with consistent structures (e.g., positive remarks first); if deployed on data with varied structures, the model may misclassify based on word positioning alone. Testing across diverse datasets and incorporating techniques like randomized sequence augmentation during training can help. However, be cautious—while auxiliary losses offer a path forward, their effectiveness in NLP-specific tasks remains under-explored, requiring careful tuning [TailoringEncodingInduc].

In summary, positional bias is a pervasive challenge in text classification, driven by architectural and training choices that prioritize superficial features. By focusing on robust design and validation practices, practitioners can mitigate these risks and build models that generalize effectively to real-world scenarios.

---

### Challenges with Sequence Learning

Sequence learning, a cornerstone of deep learning applications in natural language processing (NLP) and time-series analysis, often stumbles due to **incorrect inductive biases** that steer models toward spurious correlations instead of true underlying patterns. This misalignment results in models that fail to generalize, a critical issue for practitioners deploying systems in real-world scenarios where unseen data dominates. The following discussion unpacks the core challenges, rooted in training data distributions and model architecture, that hinder effective sequence learning.

### Inductive Bias Misalignment

Deep neural networks, while powerful, exhibit an inherent tendency to latch onto superficial patterns in data rather than generalizable hypotheses, contrary to the expectation that they avoid memorization. This issue is particularly pronounced in sequence learning tasks where models like **large language models (LLMs)** prioritize irrelevant correlations—such as background features in vision tasks or distracting sequence compositions in NLP—over core concepts [DeepNeuralNetworks]. For instance, in object recognition, models have been shown to develop a shape bias similar to that observed in children, yet this bias often misfires when applied to novel contexts, leading to incorrect inferences (Ritter et al., 2017) [LearningInductiveBiase]. The implication for practitioners is stark: models may achieve high training accuracy but collapse when faced with distributional shifts, requiring careful validation on out-of-sample data.

### Training Data and Spurious Correlations

A primary driver of these challenges lies in the training data itself, which often embeds irrelevant correlations that models exploit as shortcuts. In sequence learning for NLP, such as in **seq2seq models**, training distributions can lead to attention-based circuits that reinforce these spurious patterns rather than focusing on semantic or syntactic structures [LanguageModelsLearn]. Consider a language model trained on a synthetic factual recall task; research reveals a performance plateau during pre-training where the model forms attention mechanisms that prioritize recall over understanding, only later acquiring precise knowledge [LanguageModelsLearn]. This delay in learning true patterns means that deployed models may initially perform well but degrade as they encounter diverse inputs, a risk practitioners must mitigate through curated datasets or regularization techniques.

### Generalization Failures

Perhaps the most pressing challenge is the stark failure of generalization in sequence learning models, even when training metrics suggest success. Evidence highlights a contradiction: models can achieve near-perfect accuracy on training data yet falter on unseen examples, as seen in cases where **causal masking** in language models introduces distracting sequences that derail performance [LanguageModelsLearn]. This discrepancy shatters the myth that deep learning inherently avoids memorization, revealing a gap between theoretical expectations and practical outcomes [DeepNeuralNetworks]. For practitioners, this underscores the need for robust testing frameworks—beyond standard validation sets—that simulate real-world variability to expose these weaknesses before deployment.

> **Key Finding:** Incorrect inductive biases in sequence learning cause models to prioritize spurious correlations over true patterns, leading to generalization failures that can undermine real-world applications [DeepNeuralNetworks].

### Practical Implications and Mitigation

Addressing these challenges requires a multi-faceted approach. First, practitioners should prioritize **dataset diversity**, ensuring training data minimizes embedded biases by including varied contexts and edge cases. Second, techniques like **adversarial training** or **data augmentation** can help models unlearn shortcuts by exposing them to challenging examples during training. Finally, monitoring learning dynamics—such as the performance plateaus identified in LLMs—can guide interventions, allowing teams to adjust architectures or hyperparameters when models veer toward spurious correlations [LanguageModelsLearn]. While no silver bullet exists, these strategies collectively reduce the risk of deploying sequence learning systems that fail under pressure.

The path forward demands vigilance. By understanding the roots of inductive bias misalignment and generalization failures, practitioners can design more resilient sequence learning models. The stakes are high—missteps here can lead to costly errors in applications from automated translation to predictive analytics. Focused effort on data quality and model evaluation offers the best defense against these pervasive challenges.



## Raw LLM Response

```
{
  "call": 1,
  "section_node_id": "n11",
  "tier2_selected": ["synthesis", "theme_extraction", "comparative_analysis"],
  "analyses": {
    "synthesis": "Thesis claim: Incorrect inductive biases in language models, such as positional overfitting, systematically erode generalization by embedding spurious correlations into core learning mechanisms, a pattern that manifests across text classification and sequence learning tasks.",
    "theme_extraction": "Overfitting to Spurious Correlations: manifests in Positional Bias in Text Classification as reliance on word positions over semantic content, and in Challenges with Sequence Learning as models prioritizing irrelevant patterns like sequence compositions. Generalization Failures: manifests in Positional Bias as poor performance on shifted data distributions, and in Challenges with Sequence Learning as models failing on unseen examples due to inductive bias misalignment. Mitigation Strategies: manifests in Positional Bias through auxiliary losses and robust validation, and in Challenges with Sequence Learning via dataset diversity and adversarial training.",
    "comparative_analysis": "Key tension across children: While Positional Bias emphasizes architectural flaws like causal masking as the primary source of overfitting, Challenges with Sequence Learning highlights training data distributions as the dominant factor, revealing a progression from isolated design issues to broader data-driven vulnerabilities that demand integrated solutions for effective bias correction."
  },
  "citations_found": ["[OverfittingNlpwithDeep]", "[AnalysingImpactSequenc]", "[LearningInductiveBiase]", "[LanguageModelsLearn]"],
  "key_evidence_chunks": []
}
```

## Parsed JSON

```json
{
  "call": 1,
  "section_node_id": "n11",
  "tier2_selected": [
    "synthesis",
    "theme_extraction",
    "comparative_analysis"
  ],
  "analyses": {
    "synthesis": "Thesis claim: Incorrect inductive biases in language models, such as positional overfitting, systematically erode generalization by embedding spurious correlations into core learning mechanisms, a pattern that manifests across text classification and sequence learning tasks.",
    "theme_extraction": "Overfitting to Spurious Correlations: manifests in Positional Bias in Text Classification as reliance on word positions over semantic content, and in Challenges with Sequence Learning as models prioritizing irrelevant patterns like sequence compositions. Generalization Failures: manifests in Positional Bias as poor performance on shifted data distributions, and in Challenges with Sequence Learning as models failing on unseen examples due to inductive bias misalignment. Mitigation Strategies: manifests in Positional Bias through auxiliary losses and robust validation, and in Challenges with Sequence Learning via dataset diversity and adversarial training.",
    "comparative_analysis": "Key tension across children: While Positional Bias emphasizes architectural flaws like causal masking as the primary source of overfitting, Challenges with Sequence Learning highlights training data distributions as the dominant factor, revealing a progression from isolated design issues to broader data-driven vulnerabilities that demand integrated solutions for effective bias correction."
  },
  "citations_found": [
    "[OverfittingNlpwithDeep]",
    "[AnalysingImpactSequenc]",
    "[LearningInductiveBiase]",
    "[LanguageModelsLearn]"
  ],
  "key_evidence_chunks": []
}
```

