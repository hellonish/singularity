# `n9` — Experimental Validation of Biases
## Call 2 · Write

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


## User Message (analysis + evidence)

call: 2
section_node_id: n9
section_title: Experimental Validation of Biases
audience: practitioner

## Analysis Results (from Call 1)

{
  "synthesis": "Thesis claim: Incorrect inductive biases in deep learning models systematically undermine generalization across vision and language tasks, with experimental validation revealing consistent performance drops that demand domain-specific mitigation strategies.",
  "theme_extraction": "Performance degradation due to biases: manifests in child 1 as accuracy drops from background reliance in fruit classification, child 2 as order-induced errors in language tasks, and child 3 as overall OOD impacts across domains. Mitigation strategy effectiveness: manifests in child 1 through background masking techniques, child 2 via architectural adjustments like bidirectional attention, and child 3 as variable success in reducing bias impacts.",
  "comparative_analysis": "Key tension across children: While vision tasks (child 1) exhibit biases tied to contextual features like backgrounds, leading to 15-30% accuracy drops, language tasks (child 2) show positional biases causing 10-20% declines, and child 3 highlights that mitigation efforts, though partially effective, vary by domain, revealing a progression from specific experimental detection to broader performance measurement and the challenge of inconsistent generalization."
}

## Citations Identified

[MaskingStrategiesBackg], [Biasincomputervisionde], [TheyReAll], [EliminatingPositionBia], [MitigatePositionBias], [UnpackingBiasLarge], [BiasMitigationTechniqu]

## Children Content

### Replicating the Fruit Classification Experiment

Replicating the fruit classification experiment offers a practical way to uncover how deep learning models can mislearn features like background color as proxies for object identity due to inherent inductive biases. This section provides a structured guide for practitioners to set up, execute, and evaluate such an experiment, focusing on dataset preparation, model training, and bias assessment. By following these steps, you can observe firsthand the pitfalls of background-induced biases in vision tasks and explore mitigation strategies.

### Step 1: Dataset Setup with Controlled Backgrounds

The foundation of this experiment lies in curating a dataset that isolates background effects. Start by collecting or generating a dataset of fruit images (e.g., apples, bananas, oranges) with at least 100 samples per class to ensure sufficient variation. Use a tool like ImageNet or a custom collection, but ensure diversity in fruit appearances and poses. Critically, control the backgrounds by photographing or digitally placing fruits against uniform colors (e.g., green, blue, white) and natural scenes (e.g., grass, table surfaces). This setup mirrors findings from [MaskingStrategiesBackg], which notes that models for fine-grained classification are prone to background biases, especially with out-of-distribution (OOD) backgrounds, where accuracy can drop from 90% on in-distribution data to 60-70% on OOD settings.

To quantify background variation, split your dataset into training and test sets with a deliberate mismatch: train on fruits with consistent backgrounds (e.g., all green) and test on varied or OOD backgrounds (e.g., blue, natural scenes). This controlled discrepancy will expose how much the model relies on background cues rather than fruit features. Tools like Adobe Photoshop or Python libraries such as OpenCV can assist in background manipulation if physical setups are impractical.

### Step 2: Model Training and Configuration

Select a deep learning architecture suited for image classification, such as a pre-trained ResNet-50 or Inception-V3, available through frameworks like PyTorch or TensorFlow. Train the model on your curated dataset using standard hyperparameters: a learning rate of 0.001, batch size of 32, and 50 epochs to ensure convergence. Fine-tune the pre-trained weights to adapt to the fruit classification task, focusing on the final fully connected layer. As highlighted in [Biasincomputervisionde], biased training data can lead to skewed predictions if diversity is lacking, so monitor for overfitting to background patterns by logging training and validation accuracy.

During training, avoid augmentations that alter background context (e.g., random cropping might preserve background cues). Instead, use color jitter or rotation to emphasize fruit features. The goal is to let the model naturally learn biases if they exist, as [TheyReAll] points out that even advanced Vision Language Models (VLMs) like CLIP exhibit persistent associative biases despite mitigation efforts. Document any signs of rapid convergence on training data with high accuracy (e.g., above 85%) as a potential red flag for bias.

### Step 3: Bias Evaluation and Analysis

Post-training, evaluate the model’s performance on the test set with OOD backgrounds. Compute accuracy metrics across background types: expect a significant drop (e.g., 20-30% as per [MaskingStrategiesBackg]) when testing on unseen backgrounds. Use confusion matrices to identify specific misclassifications—does the model confuse apples on blue backgrounds with bananas more often than on green? Such patterns indicate reliance on background color over fruit shape or texture.

To further diagnose bias, apply visualization techniques like Grad-CAM to highlight regions of the image influencing predictions. If heatmaps focus on background areas rather than the fruit, this confirms the model’s misplaced attention. Additionally, test simple mitigation by masking backgrounds (e.g., setting them to black) during inference and note accuracy changes. This step aligns with insights from [TheyReAll], suggesting synthetic counterfactual images or balanced datasets as potential solutions, though not fully resolving ingrained biases.

### Practical Considerations and Limitations

This replication is resource-intensive, requiring access to GPU hardware for training and software for dataset curation. Small datasets (<100 samples per class) may amplify biases, as noted in related studies on few-shot learning. Moreover, results may vary based on the chosen architecture—simpler models might exhibit less bias but poorer overall performance. Finally, while this experiment reveals background bias, it does not fully address other biases (e.g., lighting, occlusion) that could compound errors in real-world deployment.

> **Key Finding:** Background-induced bias in fruit classification can degrade model accuracy by 20-30% on OOD settings, emphasizing the need for controlled dataset design and robust evaluation to ensure models focus on relevant object features [MaskingStrategiesBackg].

By replicating this experiment, practitioners gain actionable insights into model vulnerabilities and can begin exploring advanced mitigation strategies, such as counterfactual data generation or attention-based masking, to build more reliable vision systems.

---

### Testing Positional Bias in Language Tasks

Positional bias in language models significantly impacts performance in tasks like question answering (QA), with evidence showing up to 20% accuracy drops due to document order variations.

### Understanding Positional Bias Effects

Positional bias arises when a model's performance is influenced by the order of input data rather than its content. Experimental results on datasets like NaturalQuestions demonstrate that this bias can cause performance drops of 10-20% when documents are reordered, as detailed in studies exploring input processing mechanisms [EliminatingPositionBia][MitigatePositionBias]. The implication is clear: practitioners must account for order sensitivity when deploying models in real-world applications, particularly in multi-document QA tasks where input sequence can skew results.

### Architectural Contributions to Bias

Model architecture plays a critical role in either amplifying or mitigating positional bias. Certain design choices, especially those related to how information propagates across input tokens, can intensify bias. For instance, causal attention mechanisms often prioritize earlier tokens, leading to uneven processing of later inputs [UnpackingBiasLarge]. This suggests that architectural adjustments, such as adopting bidirectional attention, could offer a pathway to reduce bias—a strategy worth testing in custom model configurations.

### Mitigation Strategies and Their Efficacy

Several approaches have emerged to address positional bias, with varying degrees of success. One promising method involves scaling positional hidden states to normalize the influence of token order, showing improved generalization across tasks like NaturalQuestions Multi-document QA and LongBench [MitigatePositionBias]. Another approach proposes a training-free, zero-shot method by shifting from causal to bidirectional attention between documents, though residual bias persists in long-context scenarios [EliminatingPositionBia]. Practitioners should weigh these strategies based on task demands—zero-shot methods suit rapid deployment, but scaling hidden states may be more robust for complex datasets.

> **Key Finding:** While architectural tweaks and training-free methods can reduce positional bias by up to 20% in controlled experiments, complete elimination remains elusive, especially in long-context tasks [EliminatingPositionBia][UnpackingBiasLarge].

### Practical Testing Recommendations

To test for positional bias in language tasks, practitioners can adopt a structured approach:
1. **Reorder Inputs:** Systematically shuffle document or token order in test sets to measure performance variance, focusing on metrics like accuracy or F1 score.
2. **Compare Architectures:** Evaluate models with causal versus bidirectional attention on identical tasks to isolate architectural effects.
3. **Apply Mitigation:** Implement scaling of positional hidden states or zero-shot bidirectional methods, tracking bias reduction via statistical significance (e.g., p-values from repeated measures) [MitigatePositionBias].

These steps, grounded in experimental insights, can help identify and address bias in deployed systems. However, model size and dataset complexity often moderate mitigation outcomes, requiring tailored solutions for larger architectures or intricate tasks [UnpackingBiasLarge].

### Limitations and Considerations

Despite advances, current methods do not fully eliminate positional bias, particularly in long-context scenarios where residual effects linger. Meta-analyses indicate that while training-free methods enhance generalization, their impact diminishes with increased model complexity or dataset diversity [MitigatePositionBias]. Practitioners must remain vigilant, continuously testing for bias as models scale or datasets evolve, ensuring that mitigation strategies align with specific use-case constraints.

---

By integrating these testing and mitigation approaches, teams can better manage positional bias, improving model reliability in critical language tasks. Prioritizing bidirectional attention and hidden state scaling offers a practical starting point, though ongoing evaluation remains essential to adapt to emerging challenges.

---

### Measuring Impact on Model Performance

Inductive biases in machine learning models often lead to significant performance degradation, particularly in out-of-distribution (OOD) settings, with impacts varying across vision and language tasks.

### Performance Drops in OOD Settings

Statistical analysis reveals that **inductive biases**, such as positional and background biases, cause measurable declines in model performance when tested outside their training distributions. For instance, in fine-grained image classification, background biases can result in a 15-30% drop in accuracy, as models mistakenly prioritize contextual cues like background color over subtle class-specific features [MaskingStrategiesBackg]. This effect is particularly pronounced in tasks with limited samples per class, where overfitting to spurious correlations is more likely. The implication is clear: without mitigation, models risk failing in real-world scenarios where backgrounds or contexts differ from training data.

In language models (LMs), positional biases similarly impair performance. When LMs are used as judges to evaluate responses, position bias can skew results, but targeted mitigation techniques like **PINE** have shown up to a 20% improvement in task accuracy [EliminatingPositionBia]. This suggests that while biases are pervasive, their impact can be reduced with tailored interventions. Practitioners must prioritize identifying specific bias types in their models to apply the most effective countermeasures.

### Variability Across Domains and Mitigation Efforts

A meta-analysis of studies indicates that incorrect inductive biases contribute to a 10-25% performance variance across both vision and language domains, highlighting a consistent challenge in achieving generalization [EliminatingPositionBia, MaskingStrategiesBackg]. In vision tasks, biases often manifest as over-reliance on background features, such as classifying fruits based on surrounding colors rather than intrinsic properties. In language tasks, positional effects in large language models (LLMs) lead to systematic errors in sequence evaluation. This cross-domain consistency underscores the need for robust bias detection frameworks in model development pipelines.

However, mitigation strategies do not guarantee universal success. Evidence suggests that while some techniques improve performance significantly in controlled settings (with p-values below 0.05), their effectiveness varies across datasets and tasks [BiasMitigationTechniqu]. For example, certain bias reduction algorithms fail to address minority group performance, as they are often tuned to specific test sets or rely on hidden knowledge not generalizable to broader contexts. This variability necessitates a cautious approach—practitioners should validate mitigation strategies on diverse, representative datasets before deployment.

### Practical Implications and Limitations

> **Key Finding:** Inductive biases can degrade model performance by 10-30% in OOD settings, but targeted mitigation can recover significant accuracy, as seen with a 20% improvement in LM-as-a-judge tasks [EliminatingPositionBia].

For practitioners, these findings emphasize the importance of testing models under OOD conditions to expose hidden biases. Incorporating bias mitigation techniques, such as masking strategies for background biases or positional adjustments in LLMs, can yield substantial gains. However, the inconsistent success of mitigation across studies suggests that no single solution fits all scenarios—customization is key.

A critical limitation arises from the evidence base: all key studies originate from a single source domain (arxiv.org), raising concerns about potential methodological or contextual skew in reported results. This lack of source diversity may overstate or understate the true impact of biases in broader settings. Until more heterogeneous data is available, these findings should be applied with caution, and practitioners are encouraged to seek corroborating evidence from other research repositories or real-world case studies.

### Comparative Impact Across Tasks

| Task Domain          | Performance Impact (OOD) | Mitigation Effectiveness       |
|----------------------|--------------------------|-------------------------------|
| Fine-Grained Vision  | 15-30% accuracy drop     | Variable, context-dependent   |
| LM-as-a-Judge        | Up to 20% error rate     | High with targeted methods    |

The table above illustrates that while vision tasks suffer greater raw performance drops due to background biases, language tasks benefit more consistently from mitigation. This discrepancy suggests that bias in language models may be more structurally addressable through algorithmic adjustments, whereas vision biases often require deeper architectural or data-level interventions. As a result, practitioners in vision domains might need to allocate more resources to dataset curation and augmentation to counteract OOD challenges effectively.



## Raw LLM Response

```
{
  "call": 2,
  "section_node_id": "n9",
  "section_title": "Experimental Validation of Biases",
  "tier3_selected": "exec_summary",
  "content": "Incorrect inductive biases in deep learning models systematically undermine generalization across vision and language tasks, with experimental evidence revealing performance drops of 10-30% in out-of-distribution (OOD) settings that necessitate domain-specific mitigation strategies. A unifying theme across these domains is the pervasive degradation caused by biases—whether from background reliance in vision or positional effects in language—coupled with the variable success of mitigation efforts that demand tailored approaches. A key tension emerges in the nature of these biases: vision models suffer from contextual feature over-reliance, such as background colors leading to 15-30% accuracy drops, while language models exhibit order-induced errors with 10-20% performance declines, and mitigation outcomes differ significantly by task complexity and dataset diversity.\n\nIn exploring these challenges, the replication of the fruit classification experiment exposes how background-induced biases can mislead models into prioritizing irrelevant cues over object-specific features, offering practitioners actionable insights into dataset design and evaluation. Testing for positional bias in language tasks uncovers the critical role of input order in skewing results, alongside architectural adjustments like bidirectional attention as potential remedies. Finally, a broader measurement of model performance across domains quantifies the consistent impact of biases on OOD generalization, while highlighting the inconsistent effectiveness of mitigation strategies that require careful validation. \n\n> **Key Insight:** The systematic performance degradation caused by inductive biases—evident as 10-30% drops in OOD settings across vision and language tasks—reveals a critical need for domain-adapted mitigation, as no universal solution fully addresses the diverse manifestations of bias.",
  "word_count": 260,
  "citations_used": ["[MaskingStrategiesBackg]", "[EliminatingPositionBia]"],
  "coverage_gaps": []
}
```

## Parsed JSON

```json
{
  "call": 2,
  "section_node_id": "n9",
  "section_title": "Experimental Validation of Biases",
  "tier3_selected": "exec_summary",
  "content": "Incorrect inductive biases in deep learning models systematically undermine generalization across vision and language tasks, with experimental evidence revealing performance drops of 10-30% in out-of-distribution (OOD) settings that necessitate domain-specific mitigation strategies. A unifying theme across these domains is the pervasive degradation caused by biases\u2014whether from background reliance in vision or positional effects in language\u2014coupled with the variable success of mitigation efforts that demand tailored approaches. A key tension emerges in the nature of these biases: vision models suffer from contextual feature over-reliance, such as background colors leading to 15-30% accuracy drops, while language models exhibit order-induced errors with 10-20% performance declines, and mitigation outcomes differ significantly by task complexity and dataset diversity.\n\nIn exploring these challenges, the replication of the fruit classification experiment exposes how background-induced biases can mislead models into prioritizing irrelevant cues over object-specific features, offering practitioners actionable insights into dataset design and evaluation. Testing for positional bias in language tasks uncovers the critical role of input order in skewing results, alongside architectural adjustments like bidirectional attention as potential remedies. Finally, a broader measurement of model performance across domains quantifies the consistent impact of biases on OOD generalization, while highlighting the inconsistent effectiveness of mitigation strategies that require careful validation. \n\n> **Key Insight:** The systematic performance degradation caused by inductive biases\u2014evident as 10-30% drops in OOD settings across vision and language tasks\u2014reveals a critical need for domain-adapted mitigation, as no universal solution fully addresses the diverse manifestations of bias.",
  "word_count": 260,
  "citations_used": [
    "[MaskingStrategiesBackg]",
    "[EliminatingPositionBia]"
  ],
  "coverage_gaps": []
}
```

## Final Section Content (written prose)

Incorrect inductive biases in deep learning models systematically undermine generalization across vision and language tasks, with experimental evidence revealing performance drops of 10-30% in out-of-distribution (OOD) settings that necessitate domain-specific mitigation strategies. A unifying theme across these domains is the pervasive degradation caused by biases—whether from background reliance in vision or positional effects in language—coupled with the variable success of mitigation efforts that demand tailored approaches. A key tension emerges in the nature of these biases: vision models suffer from contextual feature over-reliance, such as background colors leading to 15-30% accuracy drops, while language models exhibit order-induced errors with 10-20% performance declines, and mitigation outcomes differ significantly by task complexity and dataset diversity.

In exploring these challenges, the replication of the fruit classification experiment exposes how background-induced biases can mislead models into prioritizing irrelevant cues over object-specific features, offering practitioners actionable insights into dataset design and evaluation. Testing for positional bias in language tasks uncovers the critical role of input order in skewing results, alongside architectural adjustments like bidirectional attention as potential remedies. Finally, a broader measurement of model performance across domains quantifies the consistent impact of biases on OOD generalization, while highlighting the inconsistent effectiveness of mitigation strategies that require careful validation. 

> **Key Insight:** The systematic performance degradation caused by inductive biases—evident as 10-30% drops in OOD settings across vision and language tasks—reveals a critical need for domain-adapted mitigation, as no universal solution fully addresses the diverse manifestations of bias.

