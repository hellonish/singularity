# Phase D — Polish  (section 2)

## System Prompt

# REPORT POLISHER

You are a document design editor. Your job is to make a research report section
visually excellent and easy to read — without changing any facts, data, citations,
or mathematical content.

You receive one section of a research report and return the polished version of
that same section. Return ONLY the polished markdown. No commentary, no preamble,
no code fences wrapping the output.

---

## What You May Change (Creative Licence)

**Structure & visual flow**
- Convert dense prose comparisons into tables (if 2+ attributes, 2+ items being compared)
- Convert unstructured "A, B, and C" lists into proper bullet or numbered lists
- Add horizontal rules (`---`) to separate logically distinct blocks *within* a section
- Break a wall of text (4+ sentences with no visual break) into sub-paragraphs or
  add a sub-heading

**Callouts**
- Identify the single most important claim or finding and wrap it in a blockquote:
  `> **Key Finding:** [claim]`
- If a formal definition is present, make sure it is in:
  `> **Definition:** [definition]`
- If a worked example exists, open it with:
  `> **Example:** [brief setup]`
- Do NOT add more than 2 blockquote callouts per section — choose the best candidates.

**Math rendering**
- Convert any `\(expr\)` → `$expr$` (inline)
- Convert any `\[expr\]` → `$$expr$$` (display)
- If a key equation is embedded mid-sentence and would read better as a displayed
  equation, move it to its own paragraph as `$$...$$`

**Table formatting**
- If a table exists but all rows are on one line, expand it to multi-line GFM:
  ```
  | Col A | Col B |
  |-------|-------|
  | val1  | val2  |
  ```
- If data is tab-separated without pipes, convert to GFM pipe table.
- Ensure every table has a header separator row (`|---|---|`).

**Spacing and flow**
- Ensure exactly one blank line between paragraphs (not two, not zero)
- Ensure sub-headings (`###`, `####`) are preceded and followed by a blank line
- Remove trailing whitespace from lines
- If a section has more than 5 consecutive bullet points without a break,
  consider grouping them under a `#### Sub-category` heading if logical groupings exist

---

## What You Must NOT Change

- **Facts, numbers, statistics, percentages** — preserve verbatim
- **Citation keys** `[Author2024]` — preserve every one exactly as written
- **Mathematical expressions** — preserve the LaTeX content exactly; only fix delimiters
- **Code blocks** — do not modify any content inside `` ``` `` fences
- **Substantive claims** — do not add, remove, or rephrase factual statements
- **Section headings** (`##`, `###`) — do not rename or reorder sections
- Do NOT add your own opinions, caveats, or new information

---

## Output Format

Return the polished section as plain Markdown. No wrapper text, no explanations,
no "Here is the polished version:". Just the markdown.

If a section needs no changes, return it unchanged.


## User Message

research_query: LPG Shortage in India due to US-Iran War, and multiple opinions, Prime Minister of India - Narendra Modi mentioned a lockdown might occur, I want a deep study report for this. What is India's take on it
audience: practitioner
section: 3 of 3

---BEGIN SECTION---
## Reference List

- **[WeconsiderEveryMilewed]** [‘Weconsider every milewedrive’:howfuel shortages areaffecting...](https://www.theguardian.com/world/2026/mar/24/iran-war-fuel-shortages-affecting-readers-worldwide)
- **[IndialowersFuelTaxes]** [Indialowers fuel taxes, says rumours of lockdown... | Al Jazeera](https://www.aljazeera.com/news/2026/3/27/india-slashes-petrol-diesel-import-taxes-as-fuel-prices-remain-high)
- **[IndianewsGovernmentCut]** [Indianews: Government cuts excise duties on petrol, diesel](https://www.dw.com/en/india-cuts-special-excise-duties-on-petrol-diesel-amid-iran-war/live-76555760)
- **[IndianFirmsHit]** [Indian firms hit bydisruptedgassuppliesbecause ofUS-Israelwar...](https://www.bbc.com/news/articles/cy4w92408ywo)
- **[IndianFirmsHit2]** [Indian firms hit by disrupted gassuppliesbecause of US-Israel war on...](https://www.bbc.com/news/articles/cy4w92408ywo)
- **[RussiaIndiadiscussingL]** [Russia,Indiadiscussing LNG,LPGsupplies— source... - TASS](https://tass.com/economy/2108177)
- **[IndianEconomyFinancial]** [Indian economy - Financial Times](https://www.ft.com/indian-economy)
- **[LockdownComingBackinin]** [Lockdown Coming BackinIndia? Truth Behind Viral 2026 Panic...](https://thenews21.com/lockdown-india-2026-rumours-pm-modi)
- **[WallStreetJournal]** [The Wall Street Journal - Breaking News, Business, Financial...](https://www.wsj.com/)
- **[WallStreetJournal2]** [The Wall Street Journal - Breaking News, Business, Financial...](https://www.wsj.com/)
- **[YorkTimesBreaking]** [The New York Times - Breaking News, US News,WorldNews and...](https://www.nytimes.com/)
- **[IndiaNewsToday]** [India News | Today's Top Stories | Reuters](https://www.reuters.com/world/india/)
- **[PrimeMinisterNarendra]** [Prime Minister Narendra Modi: Latest News of PM Modi | Top Stories ...](https://www.narendramodi.in/news)
- **[ReutersCom]** [reuters.com](https://www.reuters.com/)
- **[IndianewsBreakingNews]** [Indianews - breaking news, video and headlines and opinion | CNN](https://edition.cnn.com/world/india)
- **[IndiaLatestNews]** [India | Latest News & Updates | BBC News](https://www.bbc.com/news/world/asia/india)
- **[IndiaLockdownAgain]** ['India Lockdown Again?' Trends After PM Modi's Speech: Here's The Truth ...](https://www.republicworld.com/viral/india-lockdown-again-trending-pm-modi-speech-west-asia-war-2026-truth)
- **[IndianewsGovernmentCut2]** [Indianews: Government cuts excise duties on petrol, diesel](https://www.dw.com/en/india-cuts-special-excise-duties-on-petrol-diesel-amid-iran-war/live-76555760)
- **[IranwarliveIrantoClose]** [Iranwarlive:Iranto close Hormuz entirely ifUS... | Middle East Eye](https://www.middleeasteye.net/live/live-us-and-israel-attack-iran)
- **[FactCheckPm]** [Fact check: Did PM Modi hint at another lockdown in India amid ... - MSN](https://www.msn.com/en-in/politics/government/fact-check-did-pm-modi-hint-at-another-lockdown-in-india-amid-west-asia-crisis-here-s-what-he-actually-said-in-parliament/ar-AA1ZworL)
- **[BusinessNewsLive]** [Business News Live, Share Market News - Read Latest Finance News...](https://economictimes.indiatimes.com/)
- **[LockdownTrendingIndia]** [Why 'lockdown' is trending in India - The Economic Times](https://economictimes.indiatimes.com/news/new-updates/why-lockdown-is-trending-in-india-fuel-fears-rumours-explained/articleshow/129829468.cms)
- **[RealReasonsFortheus]** [The real reasons fortheUS-Israeliwar... - Geopolitical EconomyReport](https://geopoliticaleconomy.com/2025/06/17/real-reasons-us-israel-war-iran/)
- **[DayMiddleEast]** [Day 25 of Middle East conflict - Trump says ‘warhasbeen won... | CNN](https://www.cnn.com/world/live-news/iran-war-us-israel-trump-03-24-26)
- **[YahooNewsLatest]** [Yahoo News: Latest and Breaking News, Headlines, Live Updates, and...](https://news.yahoo.com/)
---END SECTION---

## Raw LLM Response

```
## Reference List

- **[WeconsiderEveryMilewed]** [‘Weconsider every milewedrive’:howfuel shortages areaffecting...](https://www.theguardian.com/world/2026/mar/24/iran-war-fuel-shortages-affecting-readers-worldwide)
- **[IndialowersFuelTaxes]** [Indialowers fuel taxes, says rumours of lockdown... | Al Jazeera](https://www.aljazeera.com/news/2026/3/27/india-slashes-petrol-diesel-import-taxes-as-fuel-prices-remain-high)
- **[IndianewsGovernmentCut]** [Indianews: Government cuts excise duties on petrol, diesel](https://www.dw.com/en/india-cuts-special-excise-duties-on-petrol-diesel-amid-iran-war/live-76555760)
- **[IndianFirmsHit]** [Indian firms hit bydisruptedgassuppliesbecause ofUS-Israelwar...](https://www.bbc.com/news/articles/cy4w92408ywo)
- **[IndianFirmsHit2]** [Indian firms hit by disrupted gassuppliesbecause of US-Israel war on...](https://www.bbc.com/news/articles/cy4w92408ywo)
- **[RussiaIndiadiscussingL]** [Russia,Indiadiscussing LNG,LPGsupplies— source... - TASS](https://tass.com/economy/2108177)
- **[IndianEconomyFinancial]** [Indian economy - Financial Times](https://www.ft.com/indian-economy)
- **[LockdownComingBackinin]** [Lockdown Coming BackinIndia? Truth Behind Viral 2026 Panic...](https://thenews21.com/lockdown-india-2026-rumours-pm-modi)
- **[WallStreetJournal]** [The Wall Street Journal - Breaking News, Business, Financial...](https://www.wsj.com/)
- **[WallStreetJournal2]** [The Wall Street Journal - Breaking News, Business, Financial...](https://www.wsj.com/)
- **[YorkTimesBreaking]** [The New York Times - Breaking News, US News,WorldNews and...](https://www.nytimes.com/)
- **[IndiaNewsToday]** [India News | Today's Top Stories | Reuters](https://www.reuters.com/world/india/)
- **[PrimeMinisterNarendra]** [Prime Minister Narendra Modi: Latest News of PM Modi | Top Stories ...](https://www.narendramodi.in/news)
- **[ReutersCom]** [reuters.com](https://www.reuters.com/)
- **[IndianewsBreakingNews]** [Indianews - breaking news, video and headlines and opinion | CNN](https://edition.cnn.com/world/india)
- **[IndiaLatestNews]** [India | Latest News & Updates | BBC News](https://www.bbc.com/news/world/asia/india)
- **[IndiaLockdownAgain]** ['India Lockdown Again?' Trends After PM Modi's Speech: Here's The Truth ...](https://www.republicworld.com/viral/india-lockdown-again-trending-pm-modi-speech-west-asia-war-2026-truth)
- **[IndianewsGovernmentCut2]** [Indianews: Government cuts excise duties on petrol, diesel](https://www.dw.com/en/india-cuts-special-excise-duties-on-petrol-diesel-amid-iran-war/live-76555760)
- **[IranwarliveIrantoClose]** [Iranwarlive:Iranto close Hormuz entirely ifUS... | Middle East Eye](https://www.middleeasteye.net/live/live-us-and-israel-attack-iran)
- **[FactCheckPm]** [Fact check: Did PM Modi hint at another lockdown in India amid ... - MSN](https://www.msn.com/en-in/politics/government/fact-check-did-pm-modi-hint-at-another-lockdown-in-india-amid-west-asia-crisis-here-s-what-he-actually-said-in-parliament/ar-AA1ZworL)
- **[BusinessNewsLive]** [Business News Live, Share Market News - Read Latest Finance News...](https://economictimes.indiatimes.com/)
- **[LockdownTrendingIndia]** [Why 'lockdown' is trending in India - The Economic Times](https://economictimes.indiatimes.com/news/new-updates/why-lockdown-is-trending-in-india-fuel-fears-rumours-explained/articleshow/129829468.cms)
- **[RealReasonsFortheus]** [The real reasons fortheUS-Israeliwar... - Geopolitical EconomyReport](https://geopoliticaleconomy.com/2025/06/17/real-reasons-us-israel-war-iran/)
- **[DayMiddleEast]** [Day 25 of Middle East conflict - Trump says ‘warhasbeen won... | CNN](https://www.cnn.com/world/live-news/iran-war-us-israel-trump-03-24-26)
- **[YahooNewsLatest]** [Yahoo News: Latest and Breaking News, Headlines, Live Updates, and...](https://news.yahoo.com/)
```

