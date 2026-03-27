# forum_search

**Tier**: retrieval  
**Name**: `forum_search`  

## Description

The `forum_search` skill is a specialized retrieval agent that physically queries and extracts structured data from public, user-generated technical forums and discussion platforms. Its primary cognitive process involves formulating targeted search queries based on an input topic, executing those queries via a web search tool constrained to specific domains, parsing the returned HTML or JSON content to identify individual discussion posts, and then transforming that raw data into a normalized, ranked set of results. The agent applies specific data transformations: it isolates key post attributes (title, body text, author, timestamp, URL), quantifies community sentiment via vote counts, identifies authoritative status (e.g., "accepted answer" on Stack Overflow), and tags each result with its source forum name. It performs credibility scoring by applying a base credibility weight (0.60 for general posts, 0.70 for Stack Overflow accepted answers) and uses these scores, along with recency and vote metrics, to rank the most relevant and trustworthy insights. The agent's output is a curated collection designed to surface practitioner experience, community consensus, and real-world problem/solution patterns that are not typically found in official documentation or static knowledge bases.

## When to Use

Use this skill in the following specific scenarios:
*   **Gauging Community Consensus:** When the task requires understanding prevailing opinions, common practices, or debates among developers and practitioners (e.g., "Is framework X preferred over Y for microservices?", "What are the common pitfalls when migrating to PostgreSQL 16?").
*   **Troubleshooting & Debugging:** When the problem involves error messages, system failures, or unexpected behavior in software, libraries, or platforms, and solutions from official docs are insufficient. The skill finds threads where users describe symptoms and share workarounds or root-cause analyses.
*   **Evaluating Real-World Usage:** When assessing the adoption, performance, or reliability of a tool, library, or API based on anecdotal evidence and user reports (e.g., "What are Reddit users saying about the stability of the latest Rust async runtime?").
*   **Finding Practical Examples & Code Snippets:** When official documentation is abstract and you need concrete, battle-tested code examples or configuration snippets shared by developers in forums like Stack Overflow.
*   **Understanding Edge Cases & Nuances:** When the topic involves non-standard use cases, integration quirks, or platform-specific behaviors that are documented primarily through community discussion.

**Upstream Dependencies & Expected Input:**
*   This skill typically requires an upstream node (e.g., a `query_planner` or `topic_analyzer`) to provide a **well-formulated, specific search query string**. The input should be a concise topic or question (e.g., "Python asyncio EventLoopPolicy Windows error"), not a broad subject area (e.g., "Python").
*   The skill expects the query to be passed as the primary task or objective. It does not parse complex instructions; it uses the input string directly for web search.

**Edge Cases - When NOT to Use This Skill:**
*   **For Factual, Verifiable Data:** Do not use for retrieving static facts, API specifications, mathematical definitions, or data best found in official documentation, textbooks, or encyclopedic sources. Use `docs_search` or `knowledge_retrieval` instead.
*   **For Highly Time-Sensitive News:** While Hacker News is included, this skill is optimized for technical discussion, not breaking news. For current events, use a dedicated `news_search` skill.
*   **When Authoritative, Single-Source Truth is Required:** Avoid using for legal, medical, or safety-critical information where community opinion is inappropriate.
*   **For Internal or Private Forums:** The tool is restricted to public domains (Stack Overflow, Reddit, Hacker News). It cannot access private, company-internal, or authenticated forums.
*   **If the Query is Vague or Philosophical:** Queries like "what is the meaning of code" or "future of programming" will yield low-quality, off-topic results.

**Downstream Nodes That Usually Follow:**
*   **`information_synthesis` or `summarize`:** To consolidate findings from multiple forum posts into a coherent summary of community wisdom.
*   **`credibility_assessment`:** To further evaluate and weight the aggregated forum evidence against other source types.
*   **`answer_formulation`:** To integrate forum-sourced solutions, code examples, or warnings into a final, comprehensive answer.
*   **`citation_formatting`:** To properly attribute the retrieved posts in the final output.

## Tools

- WebFetchTool filtered to stackoverflow.com, reddit.com, news.ycombinator.com

## Output Contract

RetrievalOutput — posts with vote_count, is_accepted_answer, forum_name

**Credibility base**: 0.60 general; 0.70 Stack Overflow accepted answer

**Min sources for OK status**: 3

## Constraints

*   **Source Domain Limitation:** The WebFetchTool must be strictly filtered to only `stackoverflow.com`, `reddit.com`, and `news.ycombinator.com` (and their subdomains, e.g., `*.stackexchange.com` may be excluded unless explicitly added). Do not attempt to fetch from blogs, personal websites, GitHub, or other forums.
*   **Credibility Scoring Protocol:** You MUST apply the defined credibility bases algorithmically. Any post from Stack Overflow that is marked as an `accepted_answer` receives a credibility score of `0.70`. All other posts (including high-scored Reddit posts or HN comments) receive a base score of `0.60`. Do not arbitrarily inflate these scores.
*   **Metadata Extraction Imperative:** For every retrieved post, you MUST extract the `vote_count` (upvotes minus downvotes, or score) and include it in the metadata. For Stack Overflow, you MUST also extract the boolean `is_accepted_answer` field. The `forum_name` (e.g., "Stack Overflow", "Reddit r/python", "Hacker News") is required.
*   **Minimum Viable Retrieval:** The skill must retrieve posts from at least **3 distinct source threads/discussions** to return an "OK" status. Fewer than 3 should trigger a "Partial" or "Poor" status, indicating insufficient data for consensus.
*   **Anti-Hallucination Directive:** The output must contain **only data directly extracted from the fetched pages**. Do not generate, infer, or summarize post content. Present the posts as discrete items with direct quotes and attributes.
*   **Token & Volume Management:** Be judicious in the number of posts retrieved per forum to manage context window limits. Prioritize posts by a combination of vote count, accepted answer status, and recency. A target of 5-7 high-quality posts total is often sufficient.
*   **Temporal Awareness:** When relevant to the query (e.g., for fast-moving technologies), prioritize newer discussions. Note the post date in metadata if available, but do not fail if the date is not present.