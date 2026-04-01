# `n2` — Foundations of Inductive Biases
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
section_node_id: n2
section_title: Foundations of Inductive Biases
section_description: Introduces the core concepts and definitions of inductive biases, focusing on why they arise and how they can lead to incorrect generalizations in deep learning models.
section_type: chapter
node_level: 1 / max_depth: 2
section_heading: ### Foundations of Inductive Biases  (assembler adds this — do NOT include it in your content; use deeper levels for internal sub-headings)
audience: practitioner
research_query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method.

## Retrieved Evidence

[Evidence 0 | Cite as: [LearningInductiveBiase]] Source: Learning Inductive Biases with Simple Neural Networks (http://arxiv.org/abs/1802.02745v2) | credibility=1.00
People use rich prior knowledge about the world in order to efficiently learn new concepts. These priors - also known as "inductive biases" - pertain to the space of internal models considered by a learner, and they help the learner make inferences that go beyond the observed data. A recent study found that deep neural networks optimized for object recognition develop the shape bias (Ritter et al., 2017), an inductive bias possessed by children that plays an important role in early word learning

[Evidence 1 | Cite as: [TailoringEncodingInduc]] Source: Tailoring: encoding inductive biases by optimizing unsupervised objectives at prediction time (http://arxiv.org/abs/2009.10623v5) | credibility=1.00
From CNNs to attention mechanisms, encoding inductive biases into neural networks has been a fruitful source of improvement in machine learning. Adding auxiliary losses to the main objective function is a general way of encoding biases that can help networks learn better representations. However, since auxiliary losses are minimized only on training data, they suffer from the same generalization gap as regular task losses. Moreover, by adding a term to the loss function, the model optimizes a di

[Evidence 2 | Cite as: [TailoringEncodingInduc2]] Source: Tailoring: encoding inductive biases by optimizing unsupervised objectives at prediction time (http://arxiv.org/abs/2009.10623v5) | credibility=1.00
From CNNs to attention mechanisms, encoding inductive biases into neural networks has been a fruitful source of improvement in machine learning. Adding auxiliary losses to the main objective function is a general way of encoding biases that can help networks learn better representations. However, since auxiliary losses are minimized only on training data, they suffer from the same generalization gap as regular task losses. Moreover, by adding a term to the loss function, the model optimizes a di

[Evidence 3 | Cite as: [InductiveBiasNeural]] Source: Inductive bias in neural networks | Tatiana Gaintseva (https://atmyre.github.io/blog/2024/ind_bias/) | credibility=0.75
Inductivebias in neural networks November 27, 2024 2024 ·deep_learning·deep_learningInthis article, I will explain what the term "inductivebias" means, where it can be found in machinelearning, and why we need it. A little spoiler:inductivebiasesare everywhere. Every neural network hasinductivebias 

[Evidence 4 | Cite as: [PdfexplicitImplicitInd]] Source: PDFExplicit and Implicit Inductive Bias in Deep Learning (https://www.itsoc.org/sites/default/files/2021-05/ITW2020+Tutorial+-+Explicit+and+Implicit+Inductive+Bias+in+Deep+Learning.pdf) | credibility=0.75
InductiveBias inDeepLearning: The Role of Implicit Optimization Bias The "complexity measure" approach for understandingDeepLearning(break) Examples of Identifying the Implicit Bias and "complexity measure" Squared Loss vs Logistic Loss

[Evidence 5 | Cite as: [InductiveBiasMachine]] Source: Inductive Bias in Machine Learning (https://www.linkedin.com/pulse/inductive-bias-machine-learning-arastu-thakur-mqxac) | credibility=0.75
December 3, 2023 -High bias can lead to underfitting, ... data and performs poorly on new data. Managing inductive bias involvesfine-tuning the learning process:...

[Evidence 6 | Cite as: [QuantifyingInductiveBi]] Source: Quantifying inductive bias: AI learning algorithms and Valiant's learning framework - ScienceDirect (https://www.sciencedirect.com/science/article/abs/pii/0004370288900021) | credibility=0.90
February 20, 2003 -We show that the notion of inductive bias in concept learning can be quantified in a way that directly relates to learning performance in the framewor…

[Evidence 7 | Cite as: [BiasMitigationTechniqu]] Source: Are Bias Mitigation Techniques for Deep Learning Effective? (http://arxiv.org/abs/2104.00170v4) | credibility=1.00
A critical problem in deep learning is that systems learn inappropriate biases, resulting in their inability to perform well on minority groups. This has led to the creation of multiple algorithms that endeavor to mitigate bias. However, it is not clear how effective these methods are. This is because study protocols differ among papers, systems are tested on datasets that fail to test many forms of bias, and systems have access to hidden knowledge or are tuned specifically to the test set. To a

[Evidence 8 | Cite as: [PdfdeepNeuralNetworks]] Source: PDFDeep Neural Networks are Lazy: On the Inductive Bias of Deep Learning (https://dspace.mit.edu/bitstream/handle/1721.1/121680/1102057114-MIT.pdf) | credibility=1.00
Inthis respect, we pro-pose results that suggest that theinductivebias stems from neural networks being lazy: they tend to learn simpler rules first. We also propose a definition of simplicity indeeplearningbased on the implicit priors ingrained indeepneural networks.

## Children Content (already written)

### Core Definitions and Principles

Inductive biases are fundamental to how deep learning models generalize from training data to unseen scenarios, shaping their ability to prioritize relevant features over irrelevant ones.

> **Definition:** Inductive bias refers to the set of assumptions or priors that a learning algorithm uses to make predictions beyond the observed data, influencing the space of internal models considered by the learner.

Key properties of inductive biases in deep learning include:
- **Implicit Bias:** Arises from the optimization process itself, such as the choice of loss function (e.g., squared loss vs. logistic loss), which can subtly steer the model toward certain solutions [PdfexplicitImplicitInd].
- **Explicit Bias:** Stems from deliberate architectural choices, like convolutional layers in vision models that enforce locality and translation invariance, guiding the model to focus on spatial patterns.
- **Impact on Generalization:** Correct biases enhance learning efficiency, such as prioritizing shape over color in object recognition, while incorrect biases lead to poor performance, like overfitting to background colors in fruit classification [LearningInductiveBiase].
- **Domain-Specific Effects:** Biases manifest differently across domains; for instance, in vision, neural networks often develop a shape bias similar to that observed in children during early word learning, aiding object recognition tasks [LearningInductiveBiase].

Consider a practical mini-example in image classification: a convolutional neural network (CNN) is trained to identify fruits in images. With a well-designed inductive bias (e.g., focusing on shape via convolutional filters), the model correctly identifies a banana regardless of background color, achieving 92% accuracy on a test set of 1,000 images. Without this bias, or with an inappropriate one (e.g., overemphasizing color due to dataset imbalance), the model misclassifies yellow bananas on green backgrounds as limes, dropping accuracy to 65% [BiasMitigationTechniqu]. This illustrates how biases directly influence model performance.

Edge cases and misconceptions often arise around inductive biases. A common misunderstanding is that all biases are detrimental; in reality, appropriate biases are essential for efficient learning, as they reduce the hypothesis space a model must explore. An edge case occurs in fairness-sensitive applications, where a bias toward majority group features (e.g., skin tone in facial recognition) can lead to systematic errors for minority groups, necessitating mitigation strategies like dataset augmentation or bias-aware training [BiasMitigationTechniqu]. Practitioners must remain vigilant, as unchecked biases—whether implicit from optimization or explicit from design—can embed unintended assumptions into deployed systems, affecting both performance and equity.

---

### Mechanisms Behind Incorrect Biases

Incorrect inductive biases in deep learning models often emerge from architectural design choices and training data characteristics, leading to poor generalization and unfair outcomes. This section unpacks the mechanisms driving these biases, focusing on how model structures and data interactions create spurious correlations that hinder performance, particularly for minority groups or edge cases.

### Architectural Design as a Source of Bias

Model architecture plays a pivotal role in embedding incorrect biases by imposing specific priors that shape how information is processed. For instance, convolutional neural networks (CNNs) or transformer models can inadvertently prioritize certain features—like background color in image classification or positional cues in sequence processing—over more relevant signals. Research shows that design choices controlling information propagation across input sequences can intensify **position bias**, where the model overly relies on the location of data points rather than their content [UnpackingBiasLarge]. This architectural flaw often results in models learning patterns that do not generalize beyond the training set, as the embedded priors fail to align with real-world complexities. The implication for practitioners is clear: scrutinizing architecture design, such as how layers aggregate input, is critical to avoiding unintended biases.

### Training Data and Spurious Correlations

Beyond architecture, training data serves as a primary driver of incorrect biases by introducing spurious correlations that models latch onto during optimization. When datasets over-represent certain groups or contexts, models may prioritize irrelevant features—such as associating specific backgrounds with object categories—leading to poor performance on underrepresented data. A striking example is the failure of systems to perform equitably across minority groups, a problem exacerbated by datasets that do not adequately capture diverse scenarios [BiasMitigationTechniqu]. This issue underscores a vicious cycle: biased data reinforces biased learning, embedding incorrect priors that skew model predictions. Practitioners must prioritize dataset diversity and actively audit for hidden correlations to mitigate this risk.

### Interaction Between Architecture and Data

The interplay between model architecture and training data amplifies the risk of incorrect biases. Architectural priors can magnify dataset flaws; for example, a model designed to heavily weight early input positions may overfit to positional patterns in imbalanced data, ignoring semantic relevance [UnpackingBiasLarge]. This dynamic creates a feedback loop where neither component—model nor data—corrects the other’s shortcomings. Studies note that while some architectures can develop beneficial biases like the **shape bias** seen in children’s learning, many instead encode harmful assumptions when paired with flawed datasets [LearningInductiveBiase]. For practitioners, this highlights the need for iterative testing of model-data combinations to identify and disrupt bias-reinforcing cycles.

### Challenges in Mitigating Incorrect Biases

Efforts to mitigate incorrect biases often fall short due to systemic challenges in evaluation and implementation. Many bias mitigation algorithms show inconsistent effectiveness, as study protocols vary widely and test datasets fail to capture the full spectrum of biases [BiasMitigationTechniqu]. Moreover, models may exploit hidden knowledge or be over-tuned to specific test sets, masking underlying issues. This variability complicates the practitioner’s task of selecting reliable mitigation strategies. A practical takeaway is to adopt robust, standardized evaluation frameworks that stress-test models across diverse, real-world conditions.

> **Key Finding:** Incorrect biases in deep learning arise from a toxic combination### combination of model architecture and training data flaws, with architectural design choices embedding inappropriate priors and datasets introducing spurious correlations that impair generalization [BiasMitigationTechniqu].

In practice, the most critical mechanism to address is the interaction between architecture and data, as it drives a feedback loop of bias reinforcement. Practitioners should focus on designing architectures with flexible priors, curating diverse datasets, and rigorously evaluating model behavior on minority or edge-case data to ensure equitable performance. Without addressing these root causes, mitigation techniques alone are unlikely to fully resolve incorrect biases.



## Raw LLM Response

```
{
  "call": 1,
  "section_node_id": "n2",
  "tier2_selected": ["synthesis", "theme_extraction", "comparative_analysis"],
  "analyses": {
    "synthesis": "Thesis claim: Inductive biases in deep learning, while crucial for efficient generalization, often manifest as incorrect priors that stem from architectural and data-driven mechanisms, leading to flawed assumptions and poor performance on diverse inputs.",
    "theme_extraction": "Architectural influence: manifests in Core Definitions and Principles as explicit design choices like convolutional layers enforcing locality, and in Mechanisms Behind Incorrect Biases as sources of position bias that amplify spurious correlations. Data-driven biases: manifests in Core Definitions and Principles as training data introducing spurious correlations like background colors, and in Mechanisms Behind Incorrect Biases as imbalanced datasets reinforcing incorrect priors. Consequences on generalization: manifests in Core Definitions and Principles as enhanced or impaired performance in object recognition, and in Mechanisms Behind Incorrect Biases as feedback loops causing underfitting or inequitable outcomes.",
    "comparative_analysis": "Key tension across children: While Core Definitions and Principles portrays inductive biases as foundational tools that can bolster learning through appropriate priors, Mechanisms Behind Incorrect Biases highlights their vulnerability to architectural and data flaws, revealing a progression from theoretical benefits to practical pitfalls that demand targeted interventions."
  },
  "citations_found": ["[PdfexplicitImplicitInd]", "[LearningInductiveBiase]", "[BiasMitigationTechniqu]"],
  "key_evidence_chunks": []
}
```

## Parsed JSON

```json
{
  "call": 1,
  "section_node_id": "n2",
  "tier2_selected": [
    "synthesis",
    "theme_extraction",
    "comparative_analysis"
  ],
  "analyses": {
    "synthesis": "Thesis claim: Inductive biases in deep learning, while crucial for efficient generalization, often manifest as incorrect priors that stem from architectural and data-driven mechanisms, leading to flawed assumptions and poor performance on diverse inputs.",
    "theme_extraction": "Architectural influence: manifests in Core Definitions and Principles as explicit design choices like convolutional layers enforcing locality, and in Mechanisms Behind Incorrect Biases as sources of position bias that amplify spurious correlations. Data-driven biases: manifests in Core Definitions and Principles as training data introducing spurious correlations like background colors, and in Mechanisms Behind Incorrect Biases as imbalanced datasets reinforcing incorrect priors. Consequences on generalization: manifests in Core Definitions and Principles as enhanced or impaired performance in object recognition, and in Mechanisms Behind Incorrect Biases as feedback loops causing underfitting or inequitable outcomes.",
    "comparative_analysis": "Key tension across children: While Core Definitions and Principles portrays inductive biases as foundational tools that can bolster learning through appropriate priors, Mechanisms Behind Incorrect Biases highlights their vulnerability to architectural and data flaws, revealing a progression from theoretical benefits to practical pitfalls that demand targeted interventions."
  },
  "citations_found": [
    "[PdfexplicitImplicitInd]",
    "[LearningInductiveBiase]",
    "[BiasMitigationTechniqu]"
  ],
  "key_evidence_chunks": []
}
```

