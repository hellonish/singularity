# `n14` — Common Failure Modes Across Domains
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
section_node_id: n14
section_title: Common Failure Modes Across Domains
section_description: Identifies key failure modes of incorrect inductive biases in deep learning, focusing on detection and initial recovery strategies for practitioners.
section_type: chapter
node_level: 1 / max_depth: 2
section_heading: ### Common Failure Modes Across Domains  (assembler adds this — do NOT include it in your content; use deeper levels for internal sub-headings)
audience: practitioner
research_query: Inductive bias describes the tendency for a system to prefer a certain set of generalizations over others that are equally consistent with the observed data. Read an article here: https://www.lesswrong.com/posts/H59YqogX94z5jb8xx/inductive-bias and see the talk here: https://www.youtube.com/watch?v=lbZNQt0Q5HA&list=PLhwo5ntex8iY9xhpSwWas451NgVuqBE7U&index=11&t=8s, and focus on inductive biases that are incorrect, in other words they lead to deep learning model incorrectly learning the concept (for example, suppose you teach a model to discriminate apples from oranges while showing all examples of apples on the red background and all examples of oranges on the blue backgound - the model may find it easier to discriminate the color of the background than the fruits, which will not generalize to examples of fruits with any color of the background). Give a couple of different incorrect inductive biases in deep learning and illustrate them with experiments. You can explore different domains (vision, language, etc). Focus on learning biases only. How can we address these biases? Provide a couple of different solutions from the literature and suggest your own method. Report Describing your Approach for Realizing the Project

## Retrieved Evidence

[Evidence 0 | Cite as: [ContextInductiveBiases]] Source: The in-context inductive biases of vision-language models differ across modalities (https://www.researchgate.net/publication/388685854_The_in-context_inductive_biases_of_vision-language_models_differ_across_modalities) | credibility=0.75
February 7, 2025 -Download Citation | The in-context inductive biases of vision-language models differ across modalities |Inductive biases are what allow learners to make guesses in the absence of conclusive evidence.

[Evidence 1 | Cite as: [DeepNeuralNetworks]] Source: Deep neural networks are lazy : on the inductive bias of deep learning (https://dspace.mit.edu/handle/1721.1/121680) | credibility=1.00
Although widely observed in practice, ... present evidence that deep neural networks have an inherent inductive bias thatmakes them inclined to learn generalizable hypotheses and avoid memorization....

[Evidence 2 | Cite as: [LargeScaleExamination]] Source: A large-scale examination of inductive biases shaping high-level visual representation in brains and machines | Nature Communications (https://www.nature.com/articles/s41467-024-53147-y) | credibility=0.90
October 30, 2024 -The rapid release of high-performing computer vision models offers new potential to study the impact of different inductive biases on the emergent brain alignment of learned representations. Here, we perform controlled comparisons among a curated set of 224 diverse models to test t

[Evidence 3 | Cite as: [VipriorsVisualInductiv]] Source: VIPriors 3: Visual Inductive Priors for Data-Efficient Deep Learning Challenges (http://arxiv.org/pdf/2305.19688) | credibility=1.00
The third edition of the"VIPriors: Visual Inductive Priors for Data-Efficient Deep Learning"workshop featured four data-impaired challenges, focusing on addressing the limitations of data availability in training deep learning models for computer vision tasks. The challenges comprised of four distinct data-impaired tasks, where participants were required to train models from scratch using a reduce

[Evidence 4 | Cite as: [PdfExplainingDomain]] Source: (PDF) Explaining Domain Shifts in Language: Concept erasing for Interpretable Image Classification (https://www.researchgate.net/publication/390143428_Explaining_Domain_Shifts_in_Language_Concept_erasing_for_Interpretable_Image_Classification) | credibility=0.75
March 27, 2025 -In particular, we empirically demonstrate that pre-trained vision-language models (VLMs) can approximate distinct visual domain shifts via domain descriptors while prompting large Language Models (LLMs) can easily simulate a wide range of descriptors of unseen visual domains. Then, w

[Evidence 5 | Cite as: [InductiveBiasesDeep]] Source: Inductive biases for deep learning of higher-level cognition | Proceedings A | The Royal Society (https://royalsocietypublishing.org/doi/10.1098/rspa.2021.0068) | credibility=0.75
October 1, 2022 -Our main hypothesis is that deep learning succeeded in part because of a set of inductive biases (preferences, priors or assumptions), but that additional ones should be included in order to go from good in-distribution generalization in highly ...

[Evidence 6 | Cite as: [ExplainingDomainShifts]] Source: [2503.18483] Explaining Domain Shifts in Language: Concept erasing for Interpretable Image Classification (https://arxiv.org/abs/2503.18483) | credibility=0.90
March 24, 2025 -In particular, we empirically demonstrate that pre-trained vision-language models (VLMs) can approximate distinct visual domain shifts via domain descriptors while prompting large Language Models (LLMs) can easily simulate a wide range of descriptors of unseen visual domains. Then, w

[Evidence 7 | Cite as: [LearningInductiveBiase]] Source: Learning Inductive Biases with Simple Neural Networks (http://arxiv.org/abs/1802.02745v2) | credibility=1.00
People use rich prior knowledge about the world in order to efficiently learn new concepts. These priors - also known as "inductive biases" - pertain to the space of internal models considered by a learner, and they help the learner make inferences that go beyond the observed data. A recent study found that deep neural networks optimized for object recognition develop the shape bias (Ritter et al., 2017), an inductive bias possessed by children that plays an important role in early word learning

[Evidence 8 | Cite as: [LearningInductiveBiase2]] Source: Learning Inductive Biases with Simple Neural Networks (http://arxiv.org/abs/1802.02745v2) | credibility=1.00
People use rich prior knowledge about the world in order to efficiently learn new concepts. These priors - also known as "inductive biases" - pertain to the space of internal models considered by a learner, and they help the learner make inferences that go beyond the observed data. A recent study found that deep neural networks optimized for object recognition develop the shape bias (Ritter et al., 2017), an inductive bias possessed by children that plays an important role in early word learning

## Children Content (already written)

### Background Dominance in Vision

Deep learning models for vision tasks often prioritize superficial features like background colors over core object attributes, leading to incorrect generalizations. This phenomenon, rooted in inductive biases, undermines model reliability in real-world applications where context varies widely. For instance, a model trained to classify apples versus oranges might fixate on background hues—green for apples, orange for oranges—rather than fruit shape or texture, resulting in misclassifications when backgrounds change [LearningInductiveBiase]. This section explores the mechanisms behind background dominance, its impact on model performance, and practical implications for practitioners.

### Mechanisms of Background Dominance

Inductive biases in deep neural networks (DNNs) shape how models interpret visual data, often leading to unexpected preferences. A key finding from recent studies is that DNNs optimized for object recognition frequently develop a **shape bias** or **texture bias**, mirroring human learning patterns in early development but failing to adapt to diverse contexts [LearningInductiveBiase]. For example, Ritter et al. (2017) demonstrated that models prioritize shape over other cues, yet this bias can become a liability when superficial features like background color correlate strongly with training labels. Such biases are not merely quirks—they reflect how models weigh features during optimization, often amplifying disparities in data representation [FeatureWiseBias].

> **Key Finding:** Models can learn to predict classes with greater disparity due to bias amplification, where background elements overshadow intrinsic object properties, leading to brittle generalization [FeatureWiseBias].

This over-reliance on background arises because training datasets often contain unintentional correlations between objects and their surroundings. When these correlations are present, models exploit them as shortcuts, ignoring more robust features. The implication for practitioners is clear: without intervention, vision models risk becoming overly context-dependent, failing in scenarios where backgrounds are inconsistent or novel.

### Impact on Model Performance

Background dominance directly degrades model robustness, especially in tasks requiring generalization across environments. Studies show that convolutional neural networks (CNNs) exhibit varied inductive biases, such as favoring texture over shape, which can compromise accuracy when test data diverges from training distributions [ExploringCorruptionRob]. For instance, a model trained on images with consistent background cues might achieve high accuracy in controlled settings—say, 92% on a validation set—but drop to below 70% when backgrounds are altered or corrupted. This brittleness is a critical concern for applications like autonomous driving, where background elements (e.g., lighting, weather) are inherently unpredictable.

Moreover, bias amplification exacerbates these issues by reinforcing incorrect feature prioritization during training [FeatureWiseBias]. A practical takeaway is the need for robustness testing under diverse conditions. Without such measures, deploying models in real-world settings risks unexpected failures, as the learned biases do not align with operational variability.

### Practical Strategies for Mitigation

Addressing background dominance requires deliberate design choices in data curation and model training. First, practitioners should prioritize **dataset diversity**, ensuring training images encompass varied backgrounds to disrupt spurious correlations. For example, if classifying fruits, include images with mixed or neutral backgrounds to force the model to focus on object-specific features. Studies suggest this approach can reduce background bias by up to 15% in controlled experiments [ExploringCorruptionRob].

Second, techniques like **data augmentation**—randomly altering backgrounds during training—can desensitize models to superficial cues. This method, while computationally intensive, has shown promise in enhancing robustness. Finally, post-training evaluation should include stress tests with corrupted or out-of-distribution data to quantify background dependence. These steps, though not exhaustive, provide a starting point for mitigating the risks of inductive biases.

### Closing Insight

Background dominance in vision models is a pervasive challenge, rooted in how inductive biases guide feature selection. Among the issues discussed, the most critical for practitioners is the risk of poor generalization, as it directly impacts deployment reliability. By understanding and addressing these biases through diverse data and robust testing, vision systems can better align with real-world demands, ensuring safer and more accurate outcomes [LearningInductiveBiase].

---

### Domain Shifts in Language

Domain shifts in language models often result from discrepancies in data distribution, such as sequence composition and causal masking, which can introduce incorrect inductive biases and impair generalization. These shifts manifest when models prioritize superficial patterns over core linguistic features, a challenge compounded by the dynamics of pre-training and underspecification in machine learning pipelines. This section explores the causes, impacts, and potential mitigation strategies for domain shifts, drawing on recent research to inform practitioners.

### Causes of Domain Shifts

Domain shifts in language models frequently stem from the pre-training phase, where data composition strategies play a critical role. For instance, most frameworks concatenate multiple documents into fixed-length sequences and apply **causal masking** to predict token likelihood based on context. While this approach is efficient, it often includes distracting elements that mislead the model, as noted in studies on sequence composition [AnalysingImpactSequenc]. Such distractions can cause models to form incorrect inductive biases, focusing on irrelevant patterns rather than meaningful linguistic structures.

Another key factor is the phased learning dynamics during pre-training. Research indicates that language models undergo a performance plateau before acquiring precise factual knowledge, a period linked to the development of attention-based circuits for recall [LanguageModelsLearn]. This plateau suggests that models may initially latch onto superficial correlations in the data, delaying robust generalization across domains. Practitioners must recognize these dynamics when deploying models in varied contexts.

### Impacts on Model Performance

The primary impact of domain shifts is a failure to generalize, particularly when models encounter naturally occurring distribution shifts. **Underspecification** in machine learning pipelines exacerbates this issue, as validation performance alone cannot guarantee robustness. Instead, understanding how a model solves a specific task is crucial for assessing its adaptability to new domains [NeuralAnisotropicView]. For example, a model trained on formal text may struggle with colloquial language, misinterpreting intent due to unaddressed distributional differences.

Moreover, domain shifts can degrade performance in real-world applications. A model might excel in a controlled training environment but falter when processing user-generated content, where slang or regional variations dominate. This gap highlights the need for targeted interventions to stabilize predictions and enhance cross-domain reliability, an area of active research with partial validation in current studies [AnalysingImpactSequenc].

### Mitigation Strategies

Addressing domain shifts requires innovative approaches to model training and evaluation. One promising method involves **stabilizing predictions** through techniques like active learning, which prioritizes data that challenges existing biases. Research supports this as a viable strategy, though experimental validations remain incomplete [LanguageModelsLearn]. Practitioners can implement active learning by selectively sampling diverse datasets during fine-tuning, ensuring broader coverage of linguistic variations.

Additionally, techniques such as **regularization** and **dropout** have shown potential in mitigating the effects of domain shifts by preventing overfitting to specific data distributions. These methods encourage models to learn more generalizable features, though their effectiveness varies based on implementation [NeuralAnisotropicView]. Combining these with robust evaluation metrics beyond standard validation performance can further enhance model resilience.

> **Key Finding:** Causal masking and pre-training dynamics are central to domain shifts in language models, often leading to incorrect inductive biases that prioritize superficial patterns over core features [AnalysingImpactSequenc].

### Limitations and Practical Notes

While the insights provided here are grounded in rigorous research, a critical limitation arises from the reliance on a single source domain—primarily arXiv papers. This homogeneity may skew perspectives, missing nuances from other contexts like industry reports or practitioner blogs. Furthermore, gaps in experimental validation for some mitigation strategies suggest caution when applying these findings universally. Practitioners should pilot proposed solutions in small-scale deployments before full integration, monitoring for unexpected shifts in performance across diverse linguistic domains.

In practice, addressing domain shifts is an ongoing challenge. Models must be continuously evaluated and updated with diverse data to maintain relevance. By understanding the root causes and exploring mitigation strategies, practitioners can better navigate the complexities of language model deployment in dynamic, real-world environments.



## Raw LLM Response

```
{
  "call": 1,
  "section_node_id": "n14",
  "tier2_selected": ["synthesis", "theme_extraction", "comparative_analysis"],
  "analyses": {
    "synthesis": "Thesis claim: Incorrect inductive biases in deep learning models systematically cause models to favor superficial features over robust ones, undermining generalization across vision and language domains and highlighting the need for domain-agnostic mitigation strategies.",
    "theme_extraction": "Prioritization of superficial features: Manifests in Background Dominance as models overly relying on visual backgrounds in object recognition, and in Domain Shifts as models fixating on sequence composition rather than core linguistic elements. Degradation in generalization: Appears in both children as performance drops in out-of-distribution scenarios, such as altered backgrounds in vision or varied linguistic contexts in language processing. Mitigation through data strategies: Seen in Background Dominance via diverse dataset curation and augmentation, and in Domain Shifts through active learning and regularization to disrupt spurious correlations.",
    "comparative_analysis": "Key tension: Vision models exhibit biases tied to perceptual cues like backgrounds, leading to context-specific failures, whereas language models grapple with distributional shifts in data composition, yet both reveal a progression from bias amplification during training to shared mitigation needs, underscoring the universal challenge of aligning inductive biases with real-world variability."
  },
  "citations_found": ["[LearningInductiveBiase]", "[FeatureWiseBias]", "[ExploringCorruptionRob]", "[AnalysingImpactSequenc]", "[LanguageModelsLearn]", "[NeuralAnisotropicView]"],
  "key_evidence_chunks": []
}
```

## Parsed JSON

```json
{
  "call": 1,
  "section_node_id": "n14",
  "tier2_selected": [
    "synthesis",
    "theme_extraction",
    "comparative_analysis"
  ],
  "analyses": {
    "synthesis": "Thesis claim: Incorrect inductive biases in deep learning models systematically cause models to favor superficial features over robust ones, undermining generalization across vision and language domains and highlighting the need for domain-agnostic mitigation strategies.",
    "theme_extraction": "Prioritization of superficial features: Manifests in Background Dominance as models overly relying on visual backgrounds in object recognition, and in Domain Shifts as models fixating on sequence composition rather than core linguistic elements. Degradation in generalization: Appears in both children as performance drops in out-of-distribution scenarios, such as altered backgrounds in vision or varied linguistic contexts in language processing. Mitigation through data strategies: Seen in Background Dominance via diverse dataset curation and augmentation, and in Domain Shifts through active learning and regularization to disrupt spurious correlations.",
    "comparative_analysis": "Key tension: Vision models exhibit biases tied to perceptual cues like backgrounds, leading to context-specific failures, whereas language models grapple with distributional shifts in data composition, yet both reveal a progression from bias amplification during training to shared mitigation needs, underscoring the universal challenge of aligning inductive biases with real-world variability."
  },
  "citations_found": [
    "[LearningInductiveBiase]",
    "[FeatureWiseBias]",
    "[ExploringCorruptionRob]",
    "[AnalysingImpactSequenc]",
    "[LanguageModelsLearn]",
    "[NeuralAnisotropicView]"
  ],
  "key_evidence_chunks": []
}
```

