# `n2` — Understanding Inductive Biases
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
section_title: Understanding Inductive Biases
section_description: Establishes the foundational concepts and definitions of inductive biases, focusing on why deep learning models prefer certain generalizations, using academic sources for theoretical grounding.
section_type: chapter
node_level: 1 / max_depth: 2
section_heading: ### Understanding Inductive Biases  (assembler adds this — do NOT include it in your content; use deeper levels for internal sub-headings)
audience: practitioner
research_query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method. Report Describing your Approach for Realizing the Project

## Retrieved Evidence

[Evidence 0 | Cite as: [DeepNeuralNetworks]] Source: Deep neural networks are lazy : on the inductive bias of deep learning (https://dspace.mit.edu/handle/1721.1/121680) | credibility=1.00
Although widely observed in practice, ... in deep learning. We present evidence thatdeep neural networks have an inherent inductive bias that makes them inclined to learn generalizable hypotheses and avoid memorization....

[Evidence 1 | Cite as: [LearningInductiveBiase]] Source: Learning Inductive Biases with Simple Neural Networks (http://arxiv.org/abs/1802.02745v2) | credibility=1.00
People use rich prior knowledge about the world in order to efficiently learn new concepts. These priors - also known as "inductive biases" - pertain to the space of internal models considered by a learner, and they help the learner make inferences that go beyond the observed data. A recent study found that deep neural networks optimized for object recognition develop the shape bias (Ritter et al., 2017), an inductive bias possessed by children that plays an important role in early word learning

[Evidence 2 | Cite as: [InductiveBiasWikipedia]] Source: Inductive bias - Wikipedia (https://en.wikipedia.org/wiki/Inductive_bias) | credibility=0.75
December 22, 2025 -The inductive bias (also known as learning bias) of a learning algorithm isthe set of assumptions that the learner uses to predict outputs of given inputs that it has not encountered. Inductive bias is anything which makes the algorithm learn one pattern instead of another pattern

[Evidence 3 | Cite as: [TailoringEncodingInduc]] Source: Tailoring: encoding inductive biases by optimizing unsupervised objectives at prediction time (http://arxiv.org/abs/2009.10623v5) | credibility=1.00
From CNNs to attention mechanisms, encoding inductive biases into neural networks has been a fruitful source of improvement in machine learning. Adding auxiliary losses to the main objective function is a general way of encoding biases that can help networks learn better representations. However, since auxiliary losses are minimized only on training data, they suffer from the same generalization gap as regular task losses. Moreover, by adding a term to the loss function, the model optimizes a di

[Evidence 4 | Cite as: [InductiveBiasMachine]] Source: What is Inductive Bias in Machine Learning? - GeeksforGeeks (https://www.geeksforgeeks.org/what-is-inductive-bias-in-machine-learning/) | credibility=0.75
June 25, 2024 -They prefer solutions where only a few features are relevant, which can improve interpretability and generalization. Inductive bias is crucial in machine learning as ithelps algorithms generalize from limited training data to unseen data.

[Evidence 5 | Cite as: [Source]] Source: 240101867 (https://grokipedia.com/page/240101867) | credibility=0.75
Inductivebiasrefers to the set of assumptions that a learning algorithm employs to predict outputs for unseen inputs, enabling it to generalize beyond the trainingdata.

[Evidence 6 | Cite as: [TypesInductiveBias]] Source: Types of Inductive Bias in ML | Analytics Steps (https://www.analyticssteps.com/blogs/types-inductive-bias-ml) | credibility=0.75
Inductive reasoning is the process of learning general principles based on particular cases.A system's propensity to favor one set of generalizations over others that are equally compatible with the observed factsis known as inductive bias.

[Evidence 7 | Cite as: [InductiveBiasesDeep]] Source: Inductive biases for deep learning of higher-level cognition | Proceedings A | The Royal Society (https://royalsocietypublishing.org/doi/10.1098/rspa.2021.0068) | credibility=0.75
October 1, 2022 -In addition to thinking about the learning and sample complexity advantage of these inductive biases, this paper links them with knowledge representation in neural networks, with the idea that by decomposing knowledge into its stable parts (like causal mechanisms) and volatile parts

[Evidence 8 | Cite as: [GoodBadUgly]] Source: The good, bad and ugly of bias in AI | CFA Institute (https://www.cfainstitute.org/insights/articles/good-bad-and-ugly-of-bias-in-ai) | credibility=0.75
Inductivebiasis also integral to ML models, allowing them to prioritize certain properties so that they can make generalizations fromtrainingdata.

## Children Content (already written)

### Defining Inductive Bias in Learning Systems

Inductive bias in learning systems serves as a fundamental mechanism that shapes how models generalize beyond the data they are trained on.

> **Definition:** Inductive bias refers to the set of assumptions or priors embedded in a learning algorithm that guide it to prefer certain solutions or generalizations over others, even in the absence of conclusive evidence.

This bias is crucial for enabling efficient learning by narrowing the hypothesis space a model considers. Below are the key properties of inductive bias in learning systems:
- **Preference for Simplicity:** Often rooted in principles like Occam's razor, inductive biases favor simpler models or solutions, reducing the risk of overfitting to noise in the data.
- **Domain-Specific Assumptions:** These biases incorporate prior knowledge about the problem domain, such as shape biases in object recognition tasks, which align with human cognitive strategies for early concept learning [LearningInductiveBiase].
- **Impact on Generalization:** While beneficial biases enhance a model's ability to generalize to unseen data, inappropriate biases—such as focusing on irrelevant features like background colors—can degrade performance, particularly for minority groups or edge cases [BiasMitigationTechniqu].

To illustrate, consider a neural network trained on a dataset of images for object recognition. If the model develops a **shape bias**, as observed in studies of deep neural networks, it prioritizes object shapes over other features like color or texture, mirroring human learning patterns during early word acquisition [LearningInductiveBiase]. For a concrete example, when presented with images of cats, the model might correctly identify a cat based on its silhouette, even if the background or fur color varies. This bias allows the model to generalize effectively to new, unseen images of cats.

However, edge cases and misconceptions arise. A common pitfall is when a model learns an **incorrect bias**, such as discriminating based on background color rather than the object itself, leading to poor performance on diverse datasets. Another misconception is that inductive biases are always explicitly programmed; in many cases, they emerge implicitly through the architecture or optimization process of the model. Understanding and managing these biases is critical for practitioners to ensure robust and fair learning systems [BiasMitigationTechniqu].

---

### Mathematical Foundations of Bias

Inductive biases in deep learning models fundamentally shape how these systems generalize from training data, often embedding preferences that can either enhance or hinder performance depending on their alignment with real-world distributions.

> **Definition:** Inductive bias refers to the set of assumptions or preferences inherent in a learning algorithm that guide it toward specific solutions over others, influencing how it generalizes beyond observed data.

### Core Mathematical Underpinnings

Inductive biases manifest as structural or functional constraints within models. For instance, convolutional neural networks (CNNs) inherently favor local spatial hierarchies due to their filter-based architecture, a bias that aids in tasks like image recognition but may fail in contexts requiring global context. Mathematically, this can be expressed as a prior over the hypothesis space, where the model prefers functions $f$ that minimize a complexity measure, such as circuit complexity. Inspired by Solomonoff's theory of inductive inference, circuit complexity offers a universal prior that is independent of the choice of universal Turing machine (UTM), relying instead on a standardized measure like Boolean circuits with operations such as NAND [CircuitComplexityFormu].

This complexity-based prior can be formalized as minimizing the description length of a function. Consider a hypothesis $h$ represented as a Boolean circuit; the bias favors $h$ with the shortest circuit size, implying a preference for simplicity. The implication is profound: models with such biases may overfit to simpler patterns, missing nuanced data structures in complex domains.

### Empirical Manifestations and Challenges

Empirical studies reveal how these biases play out in practice. Deep neural networks optimized for object recognition often develop a **shape bias**, mirroring an inductive bias in children that prioritizes shape over other features like color during early learning [LearningInductiveBiase]. This bias, while useful in controlled settings, can lead to errors when background colors or textures dominate over object shapes in real-world data. The mathematical challenge lies in quantifying this misalignment—how does one measure the divergence between a model’s bias and the true data distribution?

One approach is through auxiliary losses, which encode specific biases by adding terms to the objective function to guide representation learning. For example, an auxiliary loss might penalize deviations from a desired feature space, mathematically expressed as $L_{\text{total}} = L_{\text{task}} + \lambda L_{\text{aux}}$, where $\lambda$ weights the bias-inducing term [TailoringEncodingInduc]. However, since these losses are optimized only on training data, they inherit the same generalization gaps as primary task losses, limiting their effectiveness in unseen scenarios.

### Practical Implications and Limitations

The mathematical foundations of bias have direct implications for practitioners. When designing models, one must balance the encoded biases with the expected data environment. A model biased toward simplicity via circuit complexity might excel in constrained tasks but falter in dynamic, high-variance settings. Similarly, reliance on shape biases can misguide applications in domains where context or texture is critical.

A key limitation arises from the academic focus of current research, often lacking diverse real-world validation due to the predominance of sources from a single domain (arxiv.org). This raises concerns about the applicability of these mathematical frameworks outside controlled experiments. Practitioners should cautiously interpret these biases, testing models across varied datasets to uncover hidden generalization gaps.

### Summary of Key Biases and Measures

| Bias Type            | Mathematical Basis                       | Strength                          | Weakness                          |
|----------------------|------------------------------------------|-----------------------------------|-----------------------------------|
| Shape Bias           | Prioritization in feature space         | Effective in object recognition   | Fails with dominant backgrounds   |
| Circuit Complexity   | Minimized description length            | Universal, UTM-independent        | Overemphasizes simplicity         |
| Auxiliary Losses     | Added objective terms                   | Guides representation learning    | Suffers generalization gaps       |

In practice, circuit complexity stands out as a robust measure due to its universal applicability, yet its bias toward simplicity often requires tempering with domain-specific adjustments. Careful calibration of these mathematical biases remains essential for deploying reliable deep learning systems.

---

### Why Biases Lead to Incorrect Generalizations

Inductive biases in deep learning often steer models toward incorrect generalizations by prioritizing spurious correlations over meaningful patterns, undermining their ability to adapt to new data. This phenomenon is not a mere quirk but a fundamental challenge for practitioners deploying models in dynamic environments.

> **Key Finding:** Biases in deep learning models, such as a tendency to favor easily detectable patterns, frequently result in overfitting to irrelevant features, like mistaking background elements for object-defining traits in vision tasks [ComprehensiveReviewBia].

### Mechanism of Incorrect Generalization

Biases in neural networks, particularly those favoring simplicity or high-confidence outputs, can cause models to latch onto superficial cues rather than robust features. For instance, in object recognition tasks, models may develop a **shape bias**—a tendency to prioritize shapes over other attributes—which mirrors human learning biases but can mislead when context shifts [LearningInductiveBiase]. When a model trained on images with consistent backgrounds encounters a new setting, it often fails to generalize because it has overfitted to irrelevant background correlations instead of the object's intrinsic properties. This over-reliance on shortcuts limits the model's utility in real-world applications where variability is the norm.

### Impact of Overconfidence

Another critical issue arises from the **overconfidence problem** in deep neural networks (DNNs). Models often assign high confidence to incorrect predictions, masking their errors and making it difficult for testing methods to identify failure points [FastBoostingUncertaint]. For practitioners, this means that even well-performing models on training data might silently harbor biases that only surface in production, leading to costly missteps. A striking example is in automated systems where high-confidence errors could misclassify critical inputs, such as in medical imaging or autonomous driving.

### Tension in Bias Utility

While biases can sometimes accelerate learning by providing useful priors, their propensity to cause incorrect generalizations often overshadows these benefits. Some studies suggest that inductive biases, like those aiding early word learning in children, can be beneficial for neural networks in constrained settings [LearningInductiveBiase]. However, the dominant evidence indicates that when these biases misalign with the target environment, they amplify errors rather than mitigate them [ComprehensiveReviewBia]. This tension remains unresolved, posing a dilemma for model design: how to harness helpful biases without inviting misleading shortcuts.

### Practical Implications

For practitioners, the takeaway is clear—biases must be rigorously monitored during model training and testing phases. Techniques like adversarial testing or domain adaptation can help uncover hidden spurious correlations before deployment. Moreover, understanding that a model’s high confidence does not equate to correctness is crucial when interpreting outputs in high-stakes scenarios. By anticipating generalization failures rooted in bias, you can prioritize robustness over superficial accuracy, ensuring models perform reliably across diverse conditions.



## Raw LLM Response

```
{
  "call": 1,
  "section_node_id": "n2",
  "tier2_selected": ["synthesis", "theme_extraction", "comparative_analysis"],
  "analyses": {
    "synthesis": "Inductive biases in deep learning models systematically drive generalization by embedding preferences for simplicity and domain-specific patterns, yet these same mechanisms often precipitate errors when they prioritize spurious correlations over robust features, underscoring the need for balanced design to align biases with real-world complexities.",
    "theme_extraction": "Shape Bias: manifests in Defining Inductive Bias in Learning Systems as a prioritization of object shapes in recognition tasks, in Mathematical Foundations of Bias as an emergent property in neural networks mirroring human learning, and in Why Biases Lead to Incorrect Generalizations as a source of errors when context shifts. Preference for Simplicity: manifests in Defining Inductive Bias in Learning Systems as a principle favoring simpler models to avoid overfitting, and in Mathematical Foundations of Bias as a bias toward minimized circuit complexity in hypothesis selection. Impact on Generalization: manifests in Defining Inductive Bias in Learning Systems as a double-edged factor enhancing or degrading performance, and in Why Biases Lead to Incorrect Generalizations as a driver of overfitting to irrelevant features.",
    "comparative_analysis": "A key tension across the children lies in the dual role of inductive biases: while Defining Inductive Bias in Learning Systems and Mathematical Foundations of Bias portray them as essential tools for efficient learning and mathematical rigor, Why Biases Lead to Incorrect Generalizations highlights their propensity to cause overconfidence and misalignment, revealing a progression from theoretical benefits to practical pitfalls that demands adaptive strategies for mitigation."
  },
  "citations_found": ["[LearningInductiveBiase]", "[BiasMitigationTechniqu]", "[CircuitComplexityFormu]", "[TailoringEncodingInduc]", "[ComprehensiveReviewBia]", "[FastBoostingUncertaint]"],
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
    "synthesis": "Inductive biases in deep learning models systematically drive generalization by embedding preferences for simplicity and domain-specific patterns, yet these same mechanisms often precipitate errors when they prioritize spurious correlations over robust features, underscoring the need for balanced design to align biases with real-world complexities.",
    "theme_extraction": "Shape Bias: manifests in Defining Inductive Bias in Learning Systems as a prioritization of object shapes in recognition tasks, in Mathematical Foundations of Bias as an emergent property in neural networks mirroring human learning, and in Why Biases Lead to Incorrect Generalizations as a source of errors when context shifts. Preference for Simplicity: manifests in Defining Inductive Bias in Learning Systems as a principle favoring simpler models to avoid overfitting, and in Mathematical Foundations of Bias as a bias toward minimized circuit complexity in hypothesis selection. Impact on Generalization: manifests in Defining Inductive Bias in Learning Systems as a double-edged factor enhancing or degrading performance, and in Why Biases Lead to Incorrect Generalizations as a driver of overfitting to irrelevant features.",
    "comparative_analysis": "A key tension across the children lies in the dual role of inductive biases: while Defining Inductive Bias in Learning Systems and Mathematical Foundations of Bias portray them as essential tools for efficient learning and mathematical rigor, Why Biases Lead to Incorrect Generalizations highlights their propensity to cause overconfidence and misalignment, revealing a progression from theoretical benefits to practical pitfalls that demands adaptive strategies for mitigation."
  },
  "citations_found": [
    "[LearningInductiveBiase]",
    "[BiasMitigationTechniqu]",
    "[CircuitComplexityFormu]",
    "[TailoringEncodingInduc]",
    "[ComprehensiveReviewBia]",
    "[FastBoostingUncertaint]"
  ],
  "key_evidence_chunks": []
}
```

