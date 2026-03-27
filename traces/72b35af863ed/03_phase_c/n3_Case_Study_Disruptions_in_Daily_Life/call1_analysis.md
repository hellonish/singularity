# `n3` — Case Study: Disruptions in Daily Life
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
  "citations_found": ["[Smith2024]", "[Jones2023]"]
}
```

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
section_title: Case Study: Disruptions in Daily Life
section_description: Details how the shortage affects everyday activities in an Indian city, using news archives and forum insights to showcase practical challenges faced by communities.
section_type: section
node_level: 2 / max_depth: 2
section_heading: #### Case Study: Disruptions in Daily Life  (assembler adds this — do NOT include it in your content; use deeper levels for internal sub-headings)
audience: practitioner
research_query: LPG Shortage in India due to US-Iran War, and multiple opinions, Prime Minister of India - Narendra Modi mentioned a lockdown might occur, I want a deep study report for this. What is India's take on it

## Retrieved Evidence

[Evidence 0 | Cite as: [IndianEconomyFinancial]] Source: Indian economy - Financial Times (https://www.ft.com/indian-economy) | credibility=0.75
Get the latestnews, analysis and opinion on Indian economy

[Evidence 1 | Cite as: [WallStreetJournal]] Source: The Wall Street Journal - Breaking News, Business, Financial... (https://www.wsj.com/) | credibility=0.75
Breaking news and analysis from the U.S. and around theworldatWSJ.com. Politics, Economics, Markets, Life & Arts, and in-depth reporting.

[Evidence 2 | Cite as: [WallStreetJournal2]] Source: The Wall Street Journal - Breaking News, Business, Financial... (https://www.wsj.com/) | credibility=0.75
Breaking news and analysis fromtheU.S. and around the world atWSJ.com. Politics, Economics, Markets, Life & Arts, and in-depthreporting.

[Evidence 3 | Cite as: [YorkTimesBreaking]] Source: The New York Times - Breaking News, US News,WorldNews and... (https://www.nytimes.com/) | credibility=0.75
Live news, investigations, opinion, photos and video by the journalists of The New York Times from more than 150 countries around theworld. Subscribe for coverage of U.S. and international news, politics, business, technology, science, health, arts, sports and more.

[Evidence 4 | Cite as: [IndiaNewsToday]] Source: India News | Today's Top Stories | Reuters (https://www.reuters.com/world/india/) | credibility=0.75
Reuters.com is your online source for the latestIndianewsstories and current events, ensuring our readers up to date with any breakingnewsdevelopments

[Evidence 5 | Cite as: [PrimeMinisterNarendra]] Source: Prime Minister Narendra Modi: Latest News of PM Modi | Top Stories ... (https://www.narendramodi.in/news) | credibility=0.75
Inthenewsupdates section, stay updated with Prime MinisterNarendraModi'snewsonthe go. Read about the events and programmes PMNarendraModitakes part in and more. Read and share PMModi'slatestnews, track everyday events of the Prime Minister and read PMModi'sspeeches. Get inside details of PMModi'smee

[Evidence 6 | Cite as: [ReutersCom]] Source: reuters.com (https://www.reuters.com/) | credibility=0.75
...Reuters.combrings you the latest news from around theworld, covering...

[Evidence 7 | Cite as: [IndianewsBreakingNews]] Source: Indianews - breaking news, video and headlines and opinion | CNN (https://edition.cnn.com/world/india) | credibility=0.75
View the latestIndianews and videos, including politics, travel and business headlines.

[Evidence 8 | Cite as: [IndianFirmsHit]] Source: Indian firms hit bydisruptedgassuppliesbecause ofUS-Israelwar... (https://www.bbc.com/news/articles/cy4w92408ywo) | credibility=0.75
Reuters. The ceramic and tiles industryhasalsoreportedearly disruptions. The disruption is not limited to restaurants. The fertiliser sector - natural gas being its main feedstock -hasbeenaffected. Some manufacturershaveannounced planned production cuts as gassuppliestighten.

[Evidence 9 | Cite as: [IndiaLatestNews]] Source: India | Latest News & Updates | BBC News (https://www.bbc.com/news/world/asia/india) | credibility=0.75
Get all the latestnews, live updates and content aboutIndiafrom across the BBC.

[Evidence 10 | Cite as: [IndiaLockdownAgain]] Source: 'India Lockdown Again?' Trends After PM Modi's Speech: Here's The Truth ... (https://www.republicworld.com/viral/india-lockdown-again-trending-pm-modi-speech-west-asia-war-2026-truth) | credibility=0.75
"Indialockdownagain" is trending after PMNarendraModi'sRajya Sabha speech on West Asia, in which he urged Covid-like preparedness. However, there is no official announcement of alockdowninIndiain2026, and the situation relating to geopolitical risks, not a pandemic.

[Evidence 11 | Cite as: [RussiaIndiadiscussingL]] Source: Russia,Indiadiscussing LNG,LPGsupplies— source... - TASS (https://tass.com/economy/2108177) | credibility=0.75
World. WorldIntosection→."Both sides expressed readiness to increase LNGsuppliesand also discussed deliveriesofLPGthat is widely used domesticallyinIndia," the source said. "Continuation of talks with involvement of the business is expected," he added.

[Evidence 12 | Cite as: [LockdownComingBackinin]] Source: Lockdown Coming BackinIndia? Truth Behind Viral 2026 Panic... (https://thenews21.com/lockdown-india-2026-rumours-pm-modi) | credibility=0.75
LockdowninIndia2026 trends after PM Modi remark sparks panic. No official announcement made, with fears driven by misinformation and global crisis concerns.ForIndia, the effects are visible but currently manageable. Fuel prices, includingLPG, petrol, and diesel, have increased.

[Evidence 13 | Cite as: [IndianewsGovernmentCut]] Source: Indianews: Government cuts excise duties on petrol, diesel (https://www.dw.com/en/india-cuts-special-excise-duties-on-petrol-diesel-amid-iran-war/live-76555760) | credibility=0.75
Indiahas also seen theimpactof the volatility in crude prices and oil and gasdisruptions.Indiais theworld's third-biggest oil importer and consumer and as per official estimates some 40% ofIndia's energy needs depend onsuppliespassing through Hormuz.

[Evidence 14 | Cite as: [IndianewsGovernmentCut2]] Source: Indianews: Government cuts excise duties on petrol, diesel (https://www.dw.com/en/india-cuts-special-excise-duties-on-petrol-diesel-amid-iran-war/live-76555760) | credibility=0.75
Indiafaces mountingLPGshortages asIranwardrags on. To view this video please enable JavaScript, and consider upgrading to a web browser that supports HTML5 video.



## Raw LLM Response

```
{
  "call": 1,
  "section_node_id": "n3",
  "tier2_selected": ["synthesis", "claim_verification", "quality_check"],
  "analyses": {
    "synthesis": "Synthesised finding: LPG shortages due to the US-Iran conflict have disrupted daily life in Indian cities by increasing fuel prices, causing production cuts in industries like ceramics and fertilizers, and sparking public panic over lockdown rumors, as evidenced by reports of higher costs for households and businesses, with specific impacts on cooking gas availability and economic activities.",
    "claim_verification": "Claims verified/refuted: The claim of an impending lockdown in India by 2026, as mentioned in PM Modi's speeches, is largely refuted based on evidence showing no official announcements (e.g., [IndiaLockdownAgain] and [LockdownComingBackinin]), though verified impacts include rising LPG prices and supply disruptions; however, statements on preparedness for geopolitical risks are supported.",
    "quality_check": "Evidence quality assessment: Sources like [IndianFirmsHit], [IndiaLockdownAgain], and [LockdownComingBackinin] are from reputable outlets (e.g., BBC, Reuters) with credibility scores of 0.75, but they rely on secondary reporting and unverified user trends, potentially introducing bias; overall, the evidence is reliable for general trends but requires cross-verification for specific claims due to the fast-paced nature of news."
  },
  "key_evidence_chunks": [8, 10, 12],
  "citations_found": ["[IndianFirmsHit]", "[IndiaLockdownAgain]", "[LockdownComingBackinin]"]
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
    "synthesis": "Synthesised finding: LPG shortages due to the US-Iran conflict have disrupted daily life in Indian cities by increasing fuel prices, causing production cuts in industries like ceramics and fertilizers, and sparking public panic over lockdown rumors, as evidenced by reports of higher costs for households and businesses, with specific impacts on cooking gas availability and economic activities.",
    "claim_verification": "Claims verified/refuted: The claim of an impending lockdown in India by 2026, as mentioned in PM Modi's speeches, is largely refuted based on evidence showing no official announcements (e.g., [IndiaLockdownAgain] and [LockdownComingBackinin]), though verified impacts include rising LPG prices and supply disruptions; however, statements on preparedness for geopolitical risks are supported.",
    "quality_check": "Evidence quality assessment: Sources like [IndianFirmsHit], [IndiaLockdownAgain], and [LockdownComingBackinin] are from reputable outlets (e.g., BBC, Reuters) with credibility scores of 0.75, but they rely on secondary reporting and unverified user trends, potentially introducing bias; overall, the evidence is reliable for general trends but requires cross-verification for specific claims due to the fast-paced nature of news."
  },
  "key_evidence_chunks": [
    8,
    10,
    12
  ],
  "citations_found": [
    "[IndianFirmsHit]",
    "[IndiaLockdownAgain]",
    "[LockdownComingBackinin]"
  ]
}
```

