# book_search

**Tier**: retrieval  
**Name**: `book_search`  

## Description

This skill performs a targeted, structured search of the Google Books API to retrieve metadata and preview information for published books and specific chapters. It is a primary retrieval node designed to gather authoritative, long-form textual sources. The agent physically executes an HTTP request to the Google Books API, passing constructed query parameters. The cognitive process involves interpreting the user's information need or the Planner's directive, formulating a precise search query optimized for book discovery (often prioritizing author, title, and subject keywords), and parsing the API's JSON response. The core data transformation involves extracting a normalized set of fields from potentially large and nested API results, filtering for items with the "books#volume" kind, and compiling a list of distinct, relevant books. It specifically looks for titles, authors, publisher, published date, description, industry identifiers (like ISBN), and preview links (including `webReaderLink` for full-book previews and `embedLink` for chapter-level embeds). The skill assesses result relevance and filters out non-book items (e.g., magazine results) or items lacking critical metadata like a title.

## When to Use

Use this skill as a foundational retrieval step when the information need is best answered by published, book-length works. This is critical for establishing credible background knowledge, historical context, foundational theories, or in-depth treatises on a subject.

*   **Specific Scenarios**:
    *   The user asks for "the key concepts from the book *Thinking, Fast and Slow*."
    *   The query requires "historical accounts of the Roman Empire" or "foundational textbooks on quantum mechanics."
    *   The Planner needs to gather authoritative sources to ground a subsequent analysis or summary task.
    *   The user references a specific book title or author and seeks more information or a preview.
    *   The task involves comparing theories from different academic books.

*   **Upstream Dependencies & Expected Input**:
    *   This skill is typically triggered by the Planner based on a user query or as part of a larger DAG. It expects a clear **search query string** as its primary input. This query should be derived from the core informational need, often enriched with keywords like "book", "textbook", "author:", or subject terms. The input format is a plain text search directive.

*   **Edge Cases & When NOT to Use**:
    *   **DO NOT USE** for searching recent news articles, blog posts, or ephemeral web content (use `web_search` or `news_search`).
    *   **DO NOT USE** for looking up factual data points like population statistics, definitions, or simple formulas (use `wikipedia_search` or `web_search`).
    *   **DO NOT USE** if the query is about software documentation, API specs, or current technical forums.
    *   **AVOID** using for queries about very recent events (within the last 6-12 months), as book publishing has a long lead time.
    *   If the initial search returns insufficient results, consider broadening the query terms before deeming the skill unsuccessful.

*   **Downstream Nodes**:
    *   The retrieved book metadata and preview links are typically passed to a `retrieval_processor` or `summarization` skill for content extraction and synthesis.
    *   Outputs can feed into a `citation` or `reference_generation` skill.
    *   It can precede a `content_analysis` or `comparative_analysis` skill when multiple books on a topic are retrieved.

## Constraints

*   **API Limitations**: The Google Books API has daily usage limits and query rate limits. The skill must construct efficient, precise queries to maximize the value of each call. Avoid running multiple redundant searches with minor variations.
*   **Token & Output Limit**: The skill must consolidate results into a concise list. Do not return the full, raw API response. The output is a curated list of book objects, each with a defined schema. The Planner should not expect the full text of books, only metadata and preview links.
*   **Hallucination Prohibition**: The skill must only return books that are explicitly present in the API response. It cannot infer or create book entries based on partial data. If a book lacks a preview link, it should be noted as such, not hallucinated.
*   **Scope Confinement**: This skill searches **only** the Google Books index. It does not search library catalogs, academic databases (e.g., JSTOR), or direct publisher websites. Its credibility is tied to the comprehensiveness of Google's book indexing.
*   **Preview Availability**: Many books, especially newer or copyrighted ones, may only have limited "snippet" previews or no preview at all. The skill should clearly indicate the level of preview access (`full`, `partial`, `none`) based on the `accessViewStatus` field.
*   **Minimum Sources**: The skill's `OK` status requires at least **2** distinct, relevant book sources. If only one book is found, the status should be considered partial, and the Planner may need to trigger a complementary retrieval skill.

## Tools

- GoogleBooksTool (Google Books API, key optional)

## Output Contract

RetrievalOutput — books with authors, publishedDate, preview_link

**Credibility base**: 0.85

**Min sources for OK status**: 2